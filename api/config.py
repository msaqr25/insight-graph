from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    APP_NAME: str = "KnowledgeGraph"
    APP_VERSION: str = "0.1.0"
    DEBUG: bool = False

    DATABASE_URL: str
    DB_POOL_SIZE: int = 5
    DB_MAX_OVERFLOW: int = 10

    UPLOADS_DIR: str = "uploads"
    MAX_FILE_SIZE_MB: int = 10

    REDIS_HOST: str
    REDIS_PORT: int
    REDIS_USER: str
    REDIS_PASSWORD: str
    REDIS_DB: int = 0

    EMBEDDING_MODEL: str
    VECTOR_DIMENSION: int

    RERANKER_MODEL: str

    GOOGLE_API_KEY: str
    GENAI_MODEL: str
    COSINE_TOP_K: int = 20
    RERANK_TOP_K: int = 3

    NEO4J_URI: str = "bolt://localhost:7687"
    NEO4J_USER: str = "neo4j"
    NEO4J_PASSWORD: str
    NEO4J_DATABASE: str = "neo4j"

    CHUNK_MIN_SIZE: int = 200
    CHUNK_MAX_SIZE: int = 1000
    CHUNK_OVERLAP: int = 50


settings = Settings()  # type: ignore[call-arg]
