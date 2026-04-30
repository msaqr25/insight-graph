import asyncio
import json
import os
from pathlib import Path

import httpx
from datasets import Dataset
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain_openai import ChatOpenAI
from ragas import RunConfig, aevaluate
from ragas.embeddings import LangchainEmbeddingsWrapper
from ragas.metrics import answer_relevancy, context_recall, faithfulness

GOLDEN_DATASET_PATH = Path("api/eval/golden_dataset.json")
API_URL = os.environ.get("EVAL_API_URL", "http://localhost:8000/api")
LLM_MODEL = os.environ.get("EVAL_LLM_MODEL", "openai/gpt-oss-120b:free")
EMBED_MODEL = os.environ.get("EVAL_EMBED_MODEL", "gemini-embedding-2")
RESULTS_PATH = Path("api/eval/baseline_results.json")


def validate_response(result: dict) -> tuple[str, list[str]]:
    if not isinstance(result, dict):
        raise ValueError(f"Expected dict response, got {type(result).__name__}")
    if "answer" not in result:
        raise ValueError("Response missing 'answer' field")
    answer = result.get("answer", "")
    sources = result.get("sources", [])
    if not isinstance(sources, list):
        raise ValueError(f"Expected 'sources' to be list, got {type(sources).__name__}")
    contexts = []
    for i, source in enumerate(sources):
        if not isinstance(source, dict):
            raise ValueError(f"Source[{i}] expected dict, got {type(source).__name__}")
        if "content" not in source:
            raise ValueError(f"Source[{i}] missing 'content' field")
        contexts.append(source.get("content", ""))
    return answer, contexts


async def query_pipeline(question: str) -> dict:
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(f"{API_URL}/query", json={"question": question})
            resp.raise_for_status()
            return resp.json()
    except httpx.HTTPStatusError as e:
        raise RuntimeError(f"API returned {e.response.status_code}: {e.response.text}") from e
    except httpx.RequestError as e:
        raise RuntimeError(f"Failed to connect to API at {API_URL}: {e}") from e
    except json.JSONDecodeError as e:
        raise RuntimeError(f"Invalid JSON response from API: {e}") from e


def get_env_var(name: str) -> str:
    value = os.environ.get(name)
    if not value:
        raise ValueError(f"Required environment variable '{name}' is not set")
    return value


def compute_avg_by_type(scores: dict, question_types: list[str]) -> dict:
    if not scores:
        return {}
    metric_lengths = {metric: len(arr) for metric, arr in scores.items()}
    if len(set(metric_lengths.values())) > 1:
        raise ValueError(f"Metrics have inconsistent lengths: {metric_lengths}")
    results: dict[str, dict[str, float] | None] = {}
    for q_type in [
        "single_paper_factual",
        "cross_paper_comparison",
        "multi_hop_relational",
        "contradiction",
    ]:
        indices = [i for i, t in enumerate(question_types) if t == q_type]
        if not indices:
            results[q_type] = None
            continue
        results[q_type] = {
            metric: sum(scores[metric][i] for i in indices) / len(indices) for metric in scores
        }
    return results


async def run_evaluation():
    api_key = get_env_var("OPENROUTER_API_KEY")

    llm = ChatOpenAI(
        base_url="https://openrouter.ai/api/v1",
        api_key=api_key,
        model=LLM_MODEL,
        temperature=0,
    )

    gemini_embeddings = GoogleGenerativeAIEmbeddings(model=EMBED_MODEL, output_dimensionality=1024)
    ragas_emb = LangchainEmbeddingsWrapper(gemini_embeddings)

    with open(GOLDEN_DATASET_PATH) as f:
        golden = json.load(f)

    questions = []
    ground_truths = []
    answers = []
    contexts_list = []
    question_types = []
    raw_results = []

    print(f"Running {len(golden)} questions against the baseline pipeline...\n")

    for item in golden:
        print(f"  [{item['id']}] {item['question'][:70]}...")
        result = await query_pipeline(item["question"])

        answer, contexts = validate_response(result)

        questions.append(item["question"])
        ground_truths.append(item["ground_truth"])
        answers.append(answer)
        contexts_list.append(contexts)
        question_types.append(item["type"])

        raw_results.append(
            {
                "id": item["id"],
                "type": item["type"],
                "question": item["question"],
                "ground_truth": item["ground_truth"],
                "answer": answer,
                "contexts": contexts,
            }
        )

    # Save raw results before scoring (in case scoring fails)
    with open(RESULTS_PATH, "w") as f:
        json.dump(raw_results, f, indent=2)
    print(f"\nRaw results saved to {RESULTS_PATH}")

    # Build RAGAS dataset
    ragas_dataset = Dataset.from_dict(
        {
            "question": questions,
            "answer": answers,
            "contexts": contexts_list,
            "ground_truth": ground_truths,
        }
    )

    # Run RAGAS scoring
    run_config = RunConfig(timeout=1000)  # Avoid stupid timeout exceptions
    print("\nScoring with RAGAS...")
    scores = await aevaluate(
        ragas_dataset,
        metrics=[faithfulness, answer_relevancy, context_recall],
        llm=llm,
        embeddings=ragas_emb,
        run_config=run_config,
    )

    print("\n" + "=" * 60)
    print("BASELINE EVALUATION RESULTS")
    print("=" * 60)
    print(f"  Faithfulness:      {sum(scores['faithfulness']) / len(scores['faithfulness'])}")
    print(
        f"  Answer Relevancy:  {sum(scores['answer_relevancy']) / len(scores['answer_relevancy'])}"
    )
    print(f"  Context Recall:    {sum(scores['context_recall']) / len(scores['context_recall'])}")
    print("=" * 60)

    # Break down scores by question type
    by_type = compute_avg_by_type(scores, question_types)
    print("\nScores by question type:")
    for q_type in [
        "single_paper_factual",
        "cross_paper_comparison",
        "multi_hop_relational",
        "contradiction",
    ]:
        type_scores = by_type.get(q_type)
        if type_scores is None:
            print(f"  {q_type:30s}  (no samples)")
            continue
        print(
            f"  {q_type:30s}  faithfulness={type_scores['faithfulness']:.3f}  answer_relevancy={type_scores['answer_relevancy']:.3f}  context_recall={type_scores['context_recall']:.3f}"
        )

    # Save final scores
    final = {
        "pipeline": "baseline_vector_only",
        "scores": {
            "faithfulness": sum(scores["faithfulness"]) / len(scores["faithfulness"]),
            "answer_relevancy": sum(scores["answer_relevancy"]) / len(scores["answer_relevancy"]),
            "context_recall": sum(scores["context_recall"]) / len(scores["context_recall"]),
        },
        "by_question_type": compute_avg_by_type(scores, question_types),
    }

    score_path = Path("api/eval/baseline_scores.json")
    with open(score_path, "w") as f:
        json.dump(final, f, indent=2)
    print(f"\nFinal scores saved to {score_path}")


if __name__ == "__main__":
    asyncio.run(run_evaluation())
