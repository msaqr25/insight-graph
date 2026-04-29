import pytest
from sqlalchemy import text


class TestHealthEndpoint:
    """Integration tests for health check endpoint."""

    @pytest.mark.asyncio
    async def test_health_returns_ok(self, client):
        """Test health endpoint returns 200."""
        response = await client.get("/health")

        assert response.status_code == 200
        assert response.json() == {"status": "ok"}


class TestDatabaseConnection:
    """Integration tests for database connection."""

    @pytest.mark.asyncio
    async def test_db_session_works(self, db_session):
        """Test database session works."""
        result = await db_session.execute(text("SELECT 1"))
        value = result.scalar()
        assert value == 1

    @pytest.mark.asyncio
    async def test_pgvector_extension(self, db_session):
        """Test pgvector extension is available."""
        result = await db_session.execute(
            text("SELECT extname FROM pg_extension WHERE extname = 'vector'")
        )
        row = result.first()
        assert row is not None


class TestRedisConnection:
    """Integration tests for Redis connection."""

    @pytest.mark.asyncio
    async def test_redis_ping(self, redis_client):
        """Test Redis connection works."""
        result = await redis_client.ping()
        assert result is True

    @pytest.mark.asyncio
    async def test_redis_set_get(self, redis_client):
        """Test Redis set/get operations."""
        await redis_client.set("test_key", "test_value")
        value = await redis_client.get("test_key")
        assert value.decode() == "test_value"
