from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from api.config import settings

engine = create_engine(
    url=settings.DATABASE_URL.replace("+asyncpg", ""),
    pool_size=2,
    max_overflow=5,
)

SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)


class SessionManager:
    def __init__(self):
        self.session = SessionLocal()

    def __enter__(self) -> Session:
        return self.session

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.session.is_active:
            if exc_type:
                self.session.rollback()
            else:
                self.session.commit()
        self.session.close()
        return False


def get_session():
    return SessionManager()
