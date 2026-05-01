"""Tests for the TLE fetcher: parsing, persistence, idempotence."""

from __future__ import annotations

from datetime import UTC

import httpx
import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from oc.models import TLE, Satellite
from oc.services.tle_fetcher import (
    fetch_tle_text,
    ingest_url,
    parse_tle_text,
    persist_tles,
)

# Three real, well-formed TLEs (CelesTrak format, 2019).
SAMPLE_TLE_TEXT = """ISS (ZARYA)
1 25544U 98067A   19343.69339541  .00001764  00000-0  38792-4 0  9991
2 25544  51.6439 211.2001 0007417  17.6667  85.6398 15.50103472193511
NOAA 19
1 33591U 09005A   19343.85912442  .00000044  00000-0  44993-4 0  9994
2 33591  99.1942 320.4660 0014102 192.7402 167.3463 14.12414767559616
TERRA
1 25994U 99068A   19343.71225889  .00000023  00000-0  17041-4 0  9999
2 25994  98.2025 343.7393 0001381  90.0163 270.1158 14.57110321 65574
"""


def test_parse_tle_text_extracts_three_records() -> None:
    """A 3-line text block must produce one record per (name, line1, line2) triple."""
    parsed = parse_tle_text(SAMPLE_TLE_TEXT)
    assert len(parsed) == 3
    iss = parsed[0]
    assert iss.name == "ISS (ZARYA)"
    assert iss.norad_id == 25544
    assert iss.line1.startswith("1 25544U")
    assert iss.line2.startswith("2 25544")
    assert iss.epoch.tzinfo is UTC
    # Day 343.69339541 of 2019 -> Dec 9 2019, ~16:38 UTC
    assert iss.epoch.year == 2019 and iss.epoch.month == 12 and iss.epoch.day == 9


def test_parse_tle_text_skips_malformed_blocks() -> None:
    """A block with a malformed second line is discarded with no crash."""
    bad = (
        "BROKEN\n"
        "1 12345U 19999A   19343.69339541  .00001764  00000-0  38792-4 0  9991\n"
        "NOT A LINE 2\n"
        "ISS (ZARYA)\n"
        "1 25544U 98067A   19343.69339541  .00001764  00000-0  38792-4 0  9991\n"
        "2 25544  51.6439 211.2001 0007417  17.6667  85.6398 15.50103472193511\n"
    )
    parsed = parse_tle_text(bad)
    assert len(parsed) == 1
    assert parsed[0].name == "ISS (ZARYA)"


@pytest.mark.asyncio
async def test_persist_tles_creates_satellites_and_records(
    db_session: AsyncSession,
) -> None:
    """Persisting parsed records writes to both ``satellites`` and ``tles``."""
    parsed = parse_tle_text(SAMPLE_TLE_TEXT)
    sats, tles = await persist_tles(db_session, parsed)
    await db_session.commit()
    assert sats == 3
    assert tles == 3
    rows = (await db_session.execute(select(Satellite))).scalars().all()
    assert {s.norad_id for s in rows} == {25544, 33591, 25994}
    assert {s.name for s in rows} == {"ISS (ZARYA)", "NOAA 19", "TERRA"}
    tle_rows = (await db_session.execute(select(TLE))).scalars().all()
    assert len(tle_rows) == 3
    iss_tle = next(r for r in tle_rows if r.norad_id == 25544)
    assert iss_tle.line1.startswith("1 25544U")


@pytest.mark.asyncio
async def test_persist_tles_is_idempotent(db_session: AsyncSession) -> None:
    """Re-persisting the same parsed records produces no new TLE rows."""
    parsed = parse_tle_text(SAMPLE_TLE_TEXT)
    await persist_tles(db_session, parsed)
    await db_session.commit()
    sats2, tles2 = await persist_tles(db_session, parsed)
    await db_session.commit()
    assert sats2 == 0
    assert tles2 == 0


@pytest.mark.asyncio
async def test_ingest_url_via_mock_transport(db_session: AsyncSession) -> None:
    """End-to-end ingest: HTTP fetch -> parse -> persist using a mock transport."""

    def handler(request: httpx.Request) -> httpx.Response:
        assert "celestrak" in str(request.url)
        return httpx.Response(200, text=SAMPLE_TLE_TEXT)

    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(transport=transport) as client:
        n_parsed, n_sats, n_tles = await ingest_url(
            db_session,
            "https://celestrak.org/test",
            client=client,
        )
    await db_session.commit()
    assert (n_parsed, n_sats, n_tles) == (3, 3, 3)


@pytest.mark.asyncio
async def test_fetch_tle_text_propagates_http_errors() -> None:
    """A 5xx response must raise ``httpx.HTTPStatusError``."""

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(503, text="boom")

    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(transport=transport) as client:
        with pytest.raises(httpx.HTTPStatusError):
            await fetch_tle_text("https://celestrak.org/test", client=client)


def test_parse_handles_normalized_whitespace() -> None:
    """Trailing whitespace and blank separator lines must not break parsing."""
    text = SAMPLE_TLE_TEXT.replace("\n", " \n").replace("ISS (ZARYA) ", "ISS (ZARYA)\n\n")
    parsed = parse_tle_text(text)
    assert any(p.norad_id == 25544 for p in parsed)
    assert any(p.norad_id == 33591 for p in parsed)
