"""Async database engine and session helpers."""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Any

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase

from oc.config import Settings, get_settings


class Base(DeclarativeBase):
    """Declarative base for all ORM models."""


_engine: AsyncEngine | None = None
_sessionmaker: async_sessionmaker[AsyncSession] | None = None


def _build_engine(settings: Settings) -> AsyncEngine:
    """Construct an async engine for the configured database URL."""
    connect_args: dict[str, Any] = {}
    if settings.database_url.startswith("sqlite"):
        # SQLite needs to allow cross-thread access for the test client.
        connect_args["check_same_thread"] = False
    return create_async_engine(
        settings.database_url,
        echo=False,
        future=True,
        connect_args=connect_args,
    )


def get_engine() -> AsyncEngine:
    """Return the process-wide :class:`AsyncEngine`, creating it if needed."""
    global _engine, _sessionmaker
    if _engine is None:
        settings = get_settings()
        _engine = _build_engine(settings)
        _sessionmaker = async_sessionmaker(_engine, expire_on_commit=False, class_=AsyncSession)
    return _engine


def get_sessionmaker() -> async_sessionmaker[AsyncSession]:
    """Return the process-wide async sessionmaker."""
    if _sessionmaker is None:
        get_engine()
    assert _sessionmaker is not None
    return _sessionmaker


def reset_engine() -> None:
    """Drop cached engine/sessionmaker (used by tests)."""
    global _engine, _sessionmaker
    _engine = None
    _sessionmaker = None


def set_engine(engine: AsyncEngine) -> None:
    """Inject an existing engine (used by tests)."""
    global _engine, _sessionmaker
    _engine = engine
    _sessionmaker = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)


@asynccontextmanager
async def session_scope() -> AsyncIterator[AsyncSession]:
    """Provide a transactional scope around a series of operations."""
    sm = get_sessionmaker()
    async with sm() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


async def get_db_session() -> AsyncIterator[AsyncSession]:
    """FastAPI dependency that yields a request-scoped session."""
    sm = get_sessionmaker()
    async with sm() as session:
        try:
            yield session
        finally:
            await session.close()


async def init_models() -> None:
    """Create all tables (used in tests / first-run development)."""
    engine = get_engine()
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
