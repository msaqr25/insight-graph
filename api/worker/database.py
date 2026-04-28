from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from api.config import settings

engine = create_engine(
    url=settings.DATABASE_URL.replace("+asyncpg", ""),
    pool_size=2,
    max_overflow=5,
)

SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)


def get_db() -> Session:
    return SessionLocal()
