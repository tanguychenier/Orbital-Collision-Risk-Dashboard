"""TLE ingestion service.

Fetches CelesTrak's 3-line TLE catalogs, parses them, and persists the result
into the ``satellites`` and ``tles`` tables. The persistence step is
idempotent: an unchanged TLE (same ``epoch`` for the same ``norad_id``) is a
no-op.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

import httpx
import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from oc.config import Settings, get_settings
from oc.models import TLE, Satellite

logger = structlog.get_logger(__name__)


@dataclass(frozen=True)
class ParsedTLE:
    """A parsed 3-line TLE."""

    name: str
    norad_id: int
    line1: str
    line2: str
    epoch: datetime


class TLEParseError(ValueError):
    """Raised when a TLE block fails parsing or validation."""


def _parse_norad_id(line1: str) -> int:
    """Extract the NORAD catalog id from a TLE line 1."""
    if len(line1) < 7 or not line1.startswith("1 "):
        raise TLEParseError(f"line1 missing NORAD field: {line1!r}")
    raw = line1[2:7].strip()
    if not raw.isdigit():
        raise TLEParseError(f"NORAD id not numeric: {raw!r}")
    return int(raw)


def _parse_epoch(line1: str) -> datetime:
    """Extract the epoch (UTC) encoded in TLE line 1.

    The TLE epoch is two-digit year + day of year (with fractional day).
    Years 57-99 belong to the 1900s, 00-56 to the 2000s (Celestrak convention).
    """
    if len(line1) < 32:
        raise TLEParseError(f"line1 too short for epoch: {line1!r}")
    yr_raw = line1[18:20]
    day_raw = line1[20:32]
    try:
        yr = int(yr_raw)
        day = float(day_raw)
    except ValueError as exc:
        raise TLEParseError(f"unable to parse epoch fields: {line1!r}") from exc
    year = 1900 + yr if yr >= 57 else 2000 + yr
    base = datetime(year, 1, 1, tzinfo=UTC)
    epoch = base + timedelta(days=day - 1.0)
    return epoch


def parse_tle_text(text: str) -> list[ParsedTLE]:
    """Parse CelesTrak's standard 3-line TLE text.

    Each satellite is represented by three consecutive lines: a name line, a
    line starting with ``1 ``, and a line starting with ``2 ``.

    Lines are normalized: trailing whitespace is stripped and blank lines are
    skipped. Malformed blocks are skipped with a logged warning rather than
    aborting the whole batch.
    """
    lines = [line.rstrip() for line in text.splitlines() if line.strip()]
    parsed: list[ParsedTLE] = []
    i = 0
    while i + 2 < len(lines) + 1:
        if i + 2 >= len(lines):
            break
        name_line = lines[i]
        line1 = lines[i + 1]
        line2 = lines[i + 2]
        if not line1.startswith("1 ") or not line2.startswith("2 "):
            logger.warning("skipping malformed TLE block", index=i, name=name_line)
            i += 1
            continue
        try:
            norad_id = _parse_norad_id(line1)
            epoch = _parse_epoch(line1)
        except TLEParseError as exc:
            logger.warning("TLE parse error", error=str(exc), name=name_line)
            i += 3
            continue
        parsed.append(
            ParsedTLE(
                name=name_line.strip(),
                norad_id=norad_id,
                line1=line1,
                line2=line2,
                epoch=epoch,
            )
        )
        i += 3
    return parsed


async def fetch_tle_text(
    url: str,
    *,
    client: httpx.AsyncClient | None = None,
    timeout: float = 30.0,  # noqa: ASYNC109 -- forwarded to httpx.AsyncClient, not asyncio
) -> str:
    """Fetch a TLE document over HTTP. Returns the raw text body.

    Args:
        url: HTTP endpoint serving TLE text.
        client: Optional pre-built ``httpx.AsyncClient`` (used by tests for mocking).
        timeout: Per-request timeout in seconds (forwarded to ``httpx.AsyncClient``).
    """
    owns_client = client is None
    if client is None:
        client = httpx.AsyncClient(timeout=timeout)
    try:
        response = await client.get(url)
        response.raise_for_status()
        return response.text
    finally:
        if owns_client:
            await client.aclose()


async def persist_tles(session: AsyncSession, parsed: Iterable[ParsedTLE]) -> tuple[int, int]:
    """Persist the parsed TLEs idempotently.

    Returns:
        ``(satellites_upserted, tles_inserted)``.
    """
    sats = 0
    tles = 0
    for record in parsed:
        sat = await session.get(Satellite, record.norad_id)
        if sat is None:
            sat = Satellite(
                norad_id=record.norad_id,
                name=record.name,
                is_active=True,
            )
            session.add(sat)
            sats += 1
        else:
            if sat.name != record.name:
                sat.name = record.name
            sat.is_active = True

        existing = await session.execute(
            select(TLE).where(TLE.norad_id == record.norad_id, TLE.epoch == record.epoch)
        )
        if existing.scalar_one_or_none() is None:
            session.add(
                TLE(
                    norad_id=record.norad_id,
                    epoch=record.epoch,
                    line1=record.line1,
                    line2=record.line2,
                )
            )
            tles += 1
    await session.flush()
    return sats, tles


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
    logger.info(
        "tle ingestion complete",
        url=url,
        parsed=len(parsed),
        new_satellites=sats,
        new_tles=tles,
    )
    return len(parsed), sats, tles
