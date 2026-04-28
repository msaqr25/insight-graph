import asyncio
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import UploadFile
from httpx import ASGITransport, AsyncClient


class MockAsyncSession:
    """Mock async database session."""

    def __init__(self):
        self._data = {}
        self.committed = False
        self.refreshed = False

    def add(self, obj: Any) -> None:
        self._data[id(obj)] = obj

    async def commit(self) -> None:
        self.committed = True

    async def refresh(self, obj: Any) -> None:
        self.refreshed = True

    async def close(self) -> None:
        pass

    def query(self, model):
        return MockQuery(self._data, model)


class MockQuery:
    """Mock query builder."""

    def __init__(self, data: dict, model: Any):
        self._data = data
        self._model = model
        self._filters: list[Any] = []

    def filter(self, *conditions):
        return self

    def filter_by(self, **kwargs):
        return self

    def first(self):
        for obj in self._data.values():
            if isinstance(obj, self._model):
                return obj
        return None

    def all(self):
        return [obj for obj in self._data.values() if isinstance(obj, self._model)]


class DatabaseSessionFixture:
    """Fixture that provides a mock async database session."""

    @staticmethod
    def create():
        return MockAsyncSession()


class MockRedis:
    """Mock Redis client for ARQ."""

    def __init__(self):
        self.enqueued_jobs = []

    async def enqueue_job(self, name: str, *args, **kwargs):
        self.enqueued_jobs.append({"name": name, "args": args, "kwargs": kwargs})
        return MockJob(name)


class MockJob:
    """Mock ARQ job."""

    def __init__(self, name: str):
        self.name = name
        self.job_id = "test-job-id"


class RedisFixture:
    """Fixture that provides a mock Redis client."""

    @staticmethod
    def create():
        return MockRedis()


class MockEmbeddingModel:
    """Mock sentence transformer model."""

    def encode(self, texts, show_progress_bar=False):
        dim = 384
        if isinstance(texts, list):
            return [[0.0] * dim for _ in texts]
        return [0.0] * dim


class MockPdfDocument:
    """Mock pymupdf document."""

    def __init__(self, text: str = "Sample text from PDF"):
        self._text = text
        self._pages = [MockPage(text)]

    def __enter__(self):
        return self

    def __exit__(self, *args):
        pass

    def __iter__(self):
        return iter(self._pages)


class MockPage:
    """Mock pymupdf page."""

    def __init__(self, text: str):
        self._text = text

    def get_text(self):
        return self._text


class FileSystemFixture:
    """Fixture for temporary file system operations."""

    @staticmethod
    def create_upload_dir(tmp_path: Path) -> Path:
        upload_dir = tmp_path / "uploads"
        upload_dir.mkdir()
        return upload_dir


class UploadFileFixture:
    """Fixture for creating mock UploadFile."""

    @staticmethod
    def create_pdf(filename: str = "test.pdf", content: bytes = b"%PDF-1.4 test content"):
        mock = MagicMock(spec=UploadFile)
        mock.filename = filename
        mock.content_type = "application/pdf"

        async def read(n: int = -1):
            if n == -1:
                return content
            return content[:n]

        mock.read = AsyncMock(side_effect=read)
        return mock

    @staticmethod
    def create_non_pdf():
        mock = MagicMock(spec=UploadFile)
        mock.filename = "test.txt"
        mock.content_type = "text/plain"
        return mock


class AppFixture:
    """Fixture for test FastAPI app."""

    @staticmethod
    def create_app():
        from api.main import app

        return app


class AsyncClientFixture:
    """Fixture for async HTTP client."""

    @staticmethod
    @pytest.fixture
    async def client():
        from api.main import app

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            yield ac


@pytest.fixture
def mock_db_session():
    return DatabaseSessionFixture.create()


@pytest.fixture
def mock_redis():
    return RedisFixture.create()


@pytest.fixture
def mock_embedding_model():
    return MockEmbeddingModel()


@pytest.fixture
def mock_pdf():
    return MockPdfDocument()


@pytest.fixture
def tmp_upload_dir(tmp_path):
    return FileSystemFixture.create_upload_dir(tmp_path)


@pytest.fixture
def upload_file_pdf():
    return UploadFileFixture.create_pdf()


@pytest.fixture
def upload_file_non_pdf():
    return UploadFileFixture.create_non_pdf()


@pytest.fixture
async def async_client():
    from api.main import app

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        yield client


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()
