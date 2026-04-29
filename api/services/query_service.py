import logging
from collections.abc import Sequence
from typing import cast

from google.genai import Client
from sentence_transformers import CrossEncoder, SentenceTransformer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.config import settings
from api.models.document import DocumentChunk
from api.schemas.query import QueryResponse, SourceChunk

logger = logging.getLogger(__name__)

_embedding_model: SentenceTransformer | None = None
_cross_encoder: CrossEncoder | None = None
_genai_client: Client | None = None


def get_embedding_model() -> SentenceTransformer:
    global _embedding_model
    if _embedding_model is None:
        _embedding_model = SentenceTransformer(settings.EMBEDDING_MODEL, device="cpu")
    return _embedding_model


def get_cross_encoder() -> CrossEncoder:
    global _cross_encoder
    if _cross_encoder is None:
        _cross_encoder = CrossEncoder(settings.RERANKER_MODEL, device="cpu")
    return _cross_encoder


def get_genai_client() -> Client:
    global _genai_client
    if _genai_client is None:
        _genai_client = Client(api_key=settings.GOOGLE_API_KEY)
    return _genai_client


async def query_documents(db: AsyncSession, question: str) -> QueryResponse:
    embedding_model = get_embedding_model()
    cross_encoder = get_cross_encoder()
    genai_client = get_genai_client()

    query_embedding = embedding_model.encode(question)

    stmt = (
        select(DocumentChunk)
        .where(DocumentChunk.embedding.isnot(None))
        .order_by(DocumentChunk.embedding.cosine_distance(query_embedding.tolist()))
        .limit(settings.COSINE_TOP_K)
    )

    result = await db.execute(stmt)
    candidates = list(result.scalars().all())

    if not candidates:
        return QueryResponse(
            answer="No relevant documents found.",
            sources=[],
        )

    query_chunks_pairs: list[tuple[str, str]] = [(question, chunk.content) for chunk in candidates]
    cross_scores = cast(
        Sequence[float],
        cross_encoder.predict(cast(list[tuple[str, str]], query_chunks_pairs)),  # type: ignore[arg-type]
    )

    ranked = sorted(
        zip(candidates, cross_scores, strict=True),
        key=lambda x: x[1],
        reverse=True,
    )

    top_chunks = ranked[: settings.RERANK_TOP_K]

    context = "\n\n".join(
        f"Source {i + 1}:\n{chunk.content}" for i, (chunk, _) in enumerate(top_chunks)
    )

    prompt = f"""You are a helpful assistant. Based on the following sources, answer the user's question.

Sources:
{context}

Question: {question}

Answer:"""

    response = genai_client.models.generate_content(
        model=settings.GENAI_MODEL,
        contents=prompt,
    )

    answer = response.text if response.text else "No answer generated."

    sources = [
        SourceChunk(
            chunk_id=chunk.id,
            content=chunk.content,
            score=float(score),
        )
        for chunk, score in top_chunks
    ]

    return QueryResponse(answer=answer, sources=sources)
