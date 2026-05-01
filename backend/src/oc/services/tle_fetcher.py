"""Backwards-compatibility shim for the TLE fetcher.

The TLE parsing logic was promoted to the application layer
(:mod:`oc.application.use_cases.refresh_tles`); the HTTP fetch lives in
:mod:`oc.infrastructure.tle_sources.celestrak`; persistence lives in
:mod:`oc.infrastructure.persistence.tle_repository`. This module wires
those three together so legacy imports keep working.
"""

from __future__ import annotations

from collections.abc import Iterable

import httpx
from sqlalchemy.ext.asyncio import AsyncSession

from oc.application.use_cases.refresh_tles import (
    TLEParseError,
    parse_tle_text,
)
from oc.config import Settings, get_settings
from oc.domain.entities import ParsedTLE
from oc.infrastructure.persistence.tle_repository import SQLAlchemyTLERepository
from oc.infrastructure.tle_sources.celestrak import fetch_tle_text


async def persist_tles(session: AsyncSession, parsed: Iterable[ParsedTLE]) -> tuple[int, int]:
    """Persist the parsed TLEs idempotently. Returns ``(satellites_added, tles_added)``."""
    repository = SQLAlchemyTLERepository(session)
    return await repository.upsert_parsed_tles(parsed)


async def ingest_url(
    session: AsyncSession,
    url: str,
    *,
    client: httpx.AsyncClient | None = None,
    settings: Settings | None = None,
) -> tuple[int, int, int]:
    """Convenience: fetch ``url``, parse, and persist.

    Returns:
        ``(parsed_count, satellites_upserted, tles_inserted)``.
    """
    s = settings or get_settings()
    text = await fetch_tle_text(url, client=client, timeout=s.http_timeout_seconds)
    parsed = parse_tle_text(text)
    sats, tles = await persist_tles(session, parsed)
    return len(parsed), sats, tles


__all__ = [
    "ParsedTLE",
    "TLEParseError",
    "fetch_tle_text",
    "ingest_url",
    "parse_tle_text",
    "persist_tles",
]
