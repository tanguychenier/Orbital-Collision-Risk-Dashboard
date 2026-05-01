"""Shared test fixtures.

The fixtures here:

* override the application settings to use an in-memory SQLite database;
* spin up a fresh schema for each test;
* expose an ``async`` SQLAlchemy session and an ``httpx.AsyncClient`` aimed at
  the FastAPI app.
"""

from __future__ import annotations

from collections.abc import AsyncIterator, Iterator

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

import oc.config as config_mod
import oc.db as db_mod
from oc.db import Base
from oc.main import create_app


@pytest.fixture()
def settings_override(monkeypatch: pytest.MonkeyPatch) -> Iterator[config_mod.Settings]:
    """Override the cached settings to use SQLite in-memory."""
    config_mod.get_settings.cache_clear()
    monkeypatch.setenv("OC_DATABASE_URL", "sqlite+aiosqlite:///:memory:")
    monkeypatch.setenv("OC_ENABLE_SCHEDULER", "false")
    s = config_mod.get_settings()
    yield s
    config_mod.get_settings.cache_clear()


@pytest_asyncio.fixture()
async def db_engine(
    settings_override: config_mod.Settings,
) -> AsyncIterator[None]:
    """Create the schema in a fresh in-memory SQLite engine for the test."""
    engine = create_async_engine(
        settings_override.database_url,
        future=True,
        connect_args={"check_same_thread": False},
    )
    db_mod.set_engine(engine)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    try:
        yield
    finally:
        await engine.dispose()
        db_mod.reset_engine()


@pytest_asyncio.fixture()
async def db_session(db_engine: None) -> AsyncIterator[AsyncSession]:
    """Yield a single session for direct database manipulation."""
    sm: async_sessionmaker[AsyncSession] = db_mod.get_sessionmaker()
    async with sm() as session:
        yield session


@pytest_asyncio.fixture()
async def client(db_engine: None) -> AsyncIterator[AsyncClient]:
    """Yield an ``httpx.AsyncClient`` aimed at the FastAPI app."""
    app = create_app()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
