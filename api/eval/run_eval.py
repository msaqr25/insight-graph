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
API_URL = "http://localhost:8000/api"
RESULTS_PATH = Path("api/eval/baseline_results.json")


async def query_pipeline(question: str) -> dict:
    async with httpx.AsyncClient(timeout=None) as client:
        resp = await client.post(f"{API_URL}/query", json={"question": question})
        return resp.json()


async def run_evaluation():
    llm = ChatOpenAI(
        base_url="https://openrouter.ai/api/v1",
        api_key=os.environ["OPENROUTER_API_KEY"],
        model="openai/gpt-oss-120b:free",
        temperature=0,
    )

    gemini_embeddings = GoogleGenerativeAIEmbeddings(
        model="gemini-embedding-2", output_dimensionality=1024
    )
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

        answer = result.get("answer", "")
        sources = result.get("sources", [])
        contexts = [source.get("content", "") for source in sources]

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
    print("\nScores by question type:")
    for q_type in [
        "single_paper_factual",
        "cross_paper_comparison",
        "multi_hop_relational",
        "contradiction",
    ]:
        indices = [i for i, t in enumerate(question_types) if t == q_type]
        type_faithfulness = sum(scores["faithfulness"][i] for i in indices) / len(indices)
        type_answer_relevancy = sum(scores["answer_relevancy"][i] for i in indices) / len(indices)
        type_context_recall = sum(scores["context_recall"][i] for i in indices) / len(indices)
        print(
            f"  {q_type:30s}  faithfulness={type_faithfulness:.3f}  answer_relevancy={type_answer_relevancy:.3f}  context_recall={type_context_recall:.3f}  (n={len(indices)})"
        )

    # Save final scores
    final = {
        "pipeline": "baseline_vector_only",
        "scores": {
            "faithfulness": sum(scores["faithfulness"]) / len(scores["faithfulness"]),
            "answer_relevancy": sum(scores["answer_relevancy"]) / len(scores["answer_relevancy"]),
            "context_recall": sum(scores["context_recall"]) / len(scores["context_recall"]),
        },
        "by_question_type": {
            q_type: {
                "faithfulness": sum(
                    scores["faithfulness"][i] for i, t in enumerate(question_types) if t == q_type
                )
                / len([t for t in question_types if t == q_type]),
                "answer_relevancy": sum(
                    scores["answer_relevancy"][i]
                    for i, t in enumerate(question_types)
                    if t == q_type
                )
                / len([t for t in question_types if t == q_type]),
                "context_recall": sum(
                    scores["context_recall"][i] for i, t in enumerate(question_types) if t == q_type
                )
                / len([t for t in question_types if t == q_type]),
            }
            for q_type in [
                "single_paper_factual",
                "cross_paper_comparison",
                "multi_hop_relational",
                "contradiction",
            ]
        },
    }

    score_path = Path("api/eval/baseline_scores.json")
    with open(score_path, "w") as f:
        json.dump(final, f, indent=2)
    print(f"\nFinal scores saved to {score_path}")


if __name__ == "__main__":
    asyncio.run(run_evaluation())
