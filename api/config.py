from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="allow")

    APP_NAME: str = "KnowledgeGraph"
    APP_VERSION: str = "0.1.0"
    DEBUG: bool = False

    DATABASE_URL: str
    DB_POOL_SIZE: int = 5
    DB_MAX_OVERFLOW: int = 10

    UPLOADS_DIR: str = "uploads"
    MAX_FILE_SIZE_MB: int = 10


settings = Settings()  # type: ignore[call-arg]
