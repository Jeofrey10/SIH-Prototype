"""Database session management."""
from __future__ import annotations

from collections.abc import Generator
from typing import Any

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import get_settings


def get_engine(url: str | None = None):
    """Create a SQLAlchemy engine."""
    db_url = url or get_settings().database_url
    return create_engine(
        db_url,
        pool_pre_ping=True,
        pool_size=10,
        max_overflow=20,
        echo=False,
    )


_engine = None
_SessionFactory = None


def init_db(url: str | None = None):
    """Initialize the database engine and session factory."""
    global _engine, _SessionFactory
    _engine = get_engine(url)
    _SessionFactory = sessionmaker(bind=_engine, expire_on_commit=False)
    return _engine


def get_session_factory():
    """Get the session factory, initializing if needed."""
    global _SessionFactory
    if _SessionFactory is None:
        init_db()
    return _SessionFactory


class _SessionLocalProxy:
    """Callable proxy so SessionLocal() works seamlessly."""
    def __call__(self, *args: Any, **kwargs: Any) -> Session:
        factory = get_session_factory()
        return factory(*args, **kwargs)


SessionLocal = _SessionLocalProxy()


def get_db() -> Generator[Session, None, None]:
    """Dependency that provides a database session per request."""
    factory = get_session_factory()
    session = factory()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def get_audit_session() -> Session:
    """Get a separate session for audit logging (persists even on rollback)."""
    factory = get_session_factory()
    return factory()
