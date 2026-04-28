import os
from unittest.mock import patch


class TestSettings:
    """Tests for the Settings configuration class."""

    def test_default_values(self):
        """Test that default values are set correctly."""
        from api import config

        s = config.settings
        assert s.APP_NAME == "KnowledgeGraph"
        assert s.APP_VERSION == "0.1.0"
        assert s.UPLOADS_DIR == "uploads"
        assert s.MAX_FILE_SIZE_MB == 10
        assert s.CHUNK_MIN_SIZE == 200
        assert s.CHUNK_MAX_SIZE == 1000
        assert s.CHUNK_OVERLAP == 50

    def test_load_from_environment(self):
        """Test that settings load from environment variables."""
        env_vars = {
            "DATABASE_URL": "postgresql+asyncpg://user:pass@localhost/db",
            "REDIS_HOST": "redishost",
            "REDIS_PORT": "6380",
            "REDIS_USER": "redisuser",
            "REDIS_PASSWORD": "redispass",
            "EMBEDDING_MODEL": "test-model",
            "VECTOR_DIMENSION": "256",
        }
        with patch.dict(os.environ, env_vars):
            from importlib import reload

            import api.config

            reload(api.config)

            s = api.config.settings
            assert s.DATABASE_URL == "postgresql+asyncpg://user:pass@localhost/db"
            assert s.REDIS_HOST == "redishost"
            assert s.REDIS_PORT == 6380
            assert s.EMBEDDING_MODEL == "test-model"
            assert s.VECTOR_DIMENSION == 256

    def test_chunk_size_settings(self):
        """Test chunk size configuration."""
        env_vars = {
            "DATABASE_URL": "postgresql+asyncpg://user:pass@localhost/db",
            "REDIS_HOST": "redishost",
            "REDIS_PORT": "6380",
            "REDIS_USER": "redisuser",
            "REDIS_PASSWORD": "redispass",
            "EMBEDDING_MODEL": "test-model",
            "VECTOR_DIMENSION": "256",
            "CHUNK_MIN_SIZE": "100",
            "CHUNK_MAX_SIZE": "500",
            "CHUNK_OVERLAP": "25",
        }
        with patch.dict(os.environ, env_vars):
            from importlib import reload

            import api.config

            reload(api.config)

            s = api.config.settings
            assert s.CHUNK_MIN_SIZE == 100
            assert s.CHUNK_MAX_SIZE == 500
            assert s.CHUNK_OVERLAP == 25
