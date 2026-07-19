"""Database engine + session helpers.

All schema creation goes through SQLAlchemy ``Base.metadata`` and is created on
startup. Alembic migrations are wired up under ``backend/alembic`` for future
schema evolution; the first version uses ``create_all`` for the initial layout
and stamps the database as baseline.
"""
from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import AppConfig


_engine: Engine | None = None
_SessionLocal: sessionmaker[Session] | None = None


def init_engine(config: AppConfig) -> Engine:
    global _engine, _SessionLocal
    if _engine is not None:
        return _engine
    _engine = create_engine(
        config.db_url,
        future=True,
        connect_args={"check_same_thread": False} if config.db_url.startswith("sqlite") else {},
    )
    _SessionLocal = sessionmaker(bind=_engine, autoflush=False, autocommit=False, future=True)
    return _engine


def get_engine() -> Engine:
    if _engine is None:
        raise RuntimeError("Database engine not initialized. Call init_engine() first.")
    return _engine


def get_session_factory() -> sessionmaker[Session]:
    if _SessionLocal is None:
        raise RuntimeError("Database session factory not initialized.")
    return _SessionLocal


def get_db() -> Iterator[Session]:
    """FastAPI dependency."""
    db = get_session_factory()()
    try:
        yield db
    finally:
        db.close()


@contextmanager
def session_scope() -> Iterator[Session]:
    """Context manager for non-request code paths."""
    db = get_session_factory()()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()
