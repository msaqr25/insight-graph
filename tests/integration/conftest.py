import asyncio
import os
from collections.abc import AsyncGenerator

import pytest
import pytest_asyncio
import redis.asyncio as redis
from arq import create_pool
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from testcontainers.postgres import PostgresContainer
from testcontainers.redis import RedisContainer

from api.main import app


@pytest.fixture(scope="session")
def event_loop():
    """Create event loop for session."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session")
def docker_services(docker_ip: str = "127.0.0.1"):
    """Start PostgreSQL and Redis containers."""
    postgres = PostgresContainer(
        image="pgvector/pgvector:0.8.2-pg17",
        username="testuser",
        password="testpass",
        dbname="testdb",
    )
    postgres.start()
    postgres_port = postgres.get_exposed_port(5432)

    redis_container = RedisContainer(image="redis:7-alpine")
    redis_container.start()
    redis_port = redis_container.get_exposed_port(6379)

    os.environ["DATABASE_URL"] = (
        f"postgresql+asyncpg://testuser:testpass@{docker_ip}:{postgres_port}/testdb"
    )
    os.environ["REDIS_HOST"] = docker_ip
    os.environ["REDIS_PORT"] = str(redis_port)
    os.environ["REDIS_USER"] = ""
    os.environ["REDIS_PASSWORD"] = ""
    os.environ["EMBEDDING_MODEL"] = "sentence-transformers/all-MiniLM-L6-v2"
    os.environ["VECTOR_DIMENSION"] = "384"

    from api import config

    config.settings.DATABASE_URL = (
        f"postgresql+asyncpg://testuser:testpass@{docker_ip}:{postgres_port}/testdb"
    )
    config.settings.REDIS_HOST = docker_ip
    config.settings.REDIS_PORT = int(redis_port)
    config.settings.REDIS_USER = ""
    config.settings.REDIS_PASSWORD = ""
    config.settings.EMBEDDING_MODEL = "sentence-transformers/all-MiniLM-L6-v2"
    config.settings.VECTOR_DIMENSION = 384
    config.settings.UPLOADS_DIR = "/tmp/test_uploads"

    yield {
        "postgres": postgres,
        "redis": redis_container,
        "postgres_url": f"postgresql+asyncpg://testuser:testpass@{docker_ip}:{postgres_port}/testdb",
        "redis_host": docker_ip,
        "redis_port": redis_port,
    }

    postgres.stop()
    redis_container.stop()


@pytest_asyncio.fixture
async def db_engine(docker_services):
    """Create database engine."""
    from api.config import settings
    from api.database import Base

    engine = create_async_engine(
        settings.DATABASE_URL,
        echo=False,
        pool_size=2,
        max_overflow=5,
    )

    async with engine.begin() as conn:
        await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        await conn.run_sync(Base.metadata.create_all)

    yield engine

    await engine.dispose()


@pytest_asyncio.fixture
async def db_session(db_engine) -> AsyncGenerator[AsyncSession]:
    """Create database session."""
    async_session_maker = async_sessionmaker(
        db_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    async with async_session_maker() as session:
        yield session


@pytest_asyncio.fixture
async def redis_client(docker_services):
    """Create Redis client."""
    from api.config import settings

    client = redis.Redis(
        host=settings.REDIS_HOST,
        port=settings.REDIS_PORT,
        db=0,
    )

    yield client

    await client.flushdb()
    await client.aclose()


@pytest_asyncio.fixture
async def client(docker_services, db_engine):
    """Create test HTTP client."""
    from api import config

    config.settings.DATABASE_URL = docker_services["postgres_url"]
    config.settings.REDIS_HOST = docker_services["redis_host"]
    config.settings.REDIS_PORT = docker_services["redis_port"]

    new_maker = async_sessionmaker(
        db_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    import api.database

    api.database.async_session_maker = new_maker
    api.database.engine = db_engine

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        from api.worker.config import REDIS_SETTINGS

        app.state.arq_redis = await create_pool(REDIS_SETTINGS)

        yield ac

        await app.state.arq_redis.close()


@pytest.fixture
def sample_pdf() -> bytes:
    """Create sample PDF content."""
    return b"""%PDF-1.4
1 0 obj
<< /Type /Catalog /Pages 2 0 R >>
endobj
2 0 obj
<< /Type /Pages /Kids [3 0 R] /Count 1 >>
endobj
3 0 obj
<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 4 0 R >>
endobj
4 0 obj
<< /Length 44 >>
stream
BT
/F1 12 Tf
100 700 Td
(Test Document) Tj
ET
endstream
endobj
xref
0 5
0000000000 65535 f
0000000009 00000 n
0000000058 00000 n
0000000115 00000 n
0000000214 00000 n
trailer
<< /Size 5 /Root 1 0 R >>
startxref
103
%%EOF"""
