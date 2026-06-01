import httpx
from sentence_transformers import SentenceTransformer

from api.config import settings
from api.graph.neo4j_client import close_neo4j
from api.worker.config import REDIS_SETTINGS
from api.worker.tasks import (
    chunk_text_task,
    embed_and_store,
    extract_entities_task,
    extract_text,
)


async def startup(ctx):
    ctx["http_client"] = httpx.AsyncClient()
    ctx["embedding_model"] = SentenceTransformer(settings.EMBEDDING_MODEL, device="cpu")
    print(f"Worker started, loaded model: {settings.EMBEDDING_MODEL}")


async def shutdown(ctx):
    await ctx["http_client"].aclose()
    await close_neo4j()
    del ctx["embedding_model"]
    print("Worker shut down, resources cleaned up.")


class WorkerSettings:
    functions = [extract_text, chunk_text_task, embed_and_store, extract_entities_task]
    redis_settings = REDIS_SETTINGS
    on_startup = startup
    on_shutdown = shutdown
    max_tries = 3
    retry_delay = 60
