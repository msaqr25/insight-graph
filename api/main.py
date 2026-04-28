from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from arq import create_pool
from fastapi import FastAPI

from api.config import settings
from api.database import close_db, init_db
from api.routers.documents import router
from api.worker.config import REDIS_SETTINGS


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncGenerator[None]:
    await init_db()
    _app.state.arq_redis = await create_pool(REDIS_SETTINGS)
    yield
    await close_db()
    await _app.state.arq_redis.close()


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    debug=settings.DEBUG,
    lifespan=lifespan,
)

app.include_router(router, prefix="/api")


@app.get("/health")
async def check_health() -> dict[str, str]:
    return {"status": "ok"}
