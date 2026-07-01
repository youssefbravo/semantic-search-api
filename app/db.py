from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from .config import get_settings

settings = get_settings()

# Synchronous engine, used by BOTH the FastAPI process (endpoints run in a
# threadpool) and the Celery worker. Deliberate design choice: the real bottleneck
# in this system is the CPU-bound embedding model, not DB I/O, so async SQLAlchemy
# would add complexity for little gain. Documented in the README tradeoffs section.
engine = create_engine(settings.database_url, pool_pre_ping=True, future=True)

SessionLocal = sessionmaker(
    bind=engine, autoflush=False, autocommit=False, future=True
)


class Base(DeclarativeBase):
    pass


def get_db():
    """FastAPI dependency yielding a request-scoped session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
