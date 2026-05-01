"""Tests for ``/api/satellites/{id}`` and ``/api/satellites/{id}/conjunctions``."""

from __future__ import annotations

import uuid
from datetime import UTC, date, datetime, timedelta

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from oc.models import TLE, Conjunction, Satellite


async def _seed_satellite_dataset(session: AsyncSession) -> dict[str, object]:
    """Insert two satellites, two TLEs and two conjunctions across two TCAs.

    The first conjunction (``conj_close``) sits inside the 24h window; the
    second (``conj_far``) lands four days out, exercising the rolling window
    counters and the ``hours`` query parameter on the conjunctions endpoint.
    """
    now = datetime.now(UTC)
    iss = Satellite(
        norad_id=25544,
        name="ISS (ZARYA)",
        country="INTL",
        object_type="PAYLOAD",
        launch_date=date(1998, 11, 20),
        is_active=True,
    )
    starlink = Satellite(
        norad_id=44713,
        name="STARLINK-1007",
        country="US",
        object_type="PAYLOAD",
        launch_date=date(2019, 11, 11),
        is_active=True,
    )
    session.add_all([iss, starlink])
    await session.flush()

    tle_iss = TLE(
        norad_id=25544,
        epoch=now - timedelta(hours=2),
        line1="1 25544U 98067A   24001.00000000  .00000000  00000-0  00000+0 0    01",
        line2="2 25544  51.6000   0.0000 0000000   0.0000   0.0000 15.50000000    02",
    )
    tle_star = TLE(
        norad_id=44713,
        epoch=now - timedelta(hours=1),
        line1="1 44713U 19074A   24001.00000000  .00000000  00000-0  00000+0 0    03",
        line2="2 44713  53.0000   0.0000 0000000   0.0000   0.0000 15.06000000    04",
    )
    session.add_all([tle_iss, tle_star])
    await session.flush()

    conj_close = Conjunction(
        id=uuid.uuid4().hex,
        sat_a_norad_id=25544,
        sat_b_norad_id=44713,
        tle_a_id=tle_iss.id,
        tle_b_id=tle_star.id,
        tca=now + timedelta(hours=12),
        miss_distance_km=0.42,
        relative_velocity_km_s=14.3,
        probability=0.0034,
    )
    conj_far = Conjunction(
        id=uuid.uuid4().hex,
        sat_a_norad_id=25544,
        sat_b_norad_id=44713,
        tle_a_id=tle_iss.id,
        tle_b_id=tle_star.id,
        tca=now + timedelta(days=4),
        miss_distance_km=2.10,
        relative_velocity_km_s=12.0,
        probability=0.00018,
    )
    session.add_all([conj_close, conj_far])
    await session.commit()
    return {"conj_close_id": conj_close.id, "conj_far_id": conj_far.id}


@pytest.mark.asyncio
async def test_satellite_detail_404_on_unknown_identifier(client: AsyncClient) -> None:
    """An unknown NORAD id must return a 404 with a ``detail`` payload."""
    response = await client.get("/api/satellites/99999999")
    assert response.status_code == 404
    assert response.json() == {"detail": "satellite not found"}


@pytest.mark.asyncio
async def test_satellite_detail_exact_match_by_norad_id(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    """An exact NORAD id must return the satellite, last TLE epoch and rolling counts."""
    await _seed_satellite_dataset(db_session)
    response = await client.get("/api/satellites/25544")
    assert response.status_code == 200
    body = response.json()
    assert body["satellite"]["norad_id"] == 25544
    assert body["satellite"]["name"] == "ISS (ZARYA)"
    assert body["satellite"]["country"] == "INTL"
    assert body["satellite"]["type"] == "PAYLOAD"
    assert body["last_tle_epoch"] is not None
    # The 12h-out conjunction is in 24h; the 4d-out one only in 7d.
    assert body["stats"]["next_24h"] == 1
    assert body["stats"]["next_72h"] == 1
    assert body["stats"]["next_7d"] == 2


@pytest.mark.asyncio
async def test_satellite_search_fuzzy_by_name(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    """The search endpoint must match on a case-insensitive name substring."""
    await _seed_satellite_dataset(db_session)
    response = await client.get("/api/satellites/search", params={"q": "starl"})
    assert response.status_code == 200
    body = response.json()
    assert len(body) == 1
    assert body[0]["norad_id"] == 44713
    assert body[0]["name"] == "STARLINK-1007"

    digit = await client.get("/api/satellites/search", params={"q": "25544"})
    assert digit.status_code == 200
    digit_body = digit.json()
    assert {row["norad_id"] for row in digit_body} == {25544}


@pytest.mark.asyncio
async def test_satellite_conjunctions_filter_window(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    """The ``hours`` query parameter must hide conjunctions past the horizon."""
    await _seed_satellite_dataset(db_session)
    # 48h: only the close conjunction (12h ahead) qualifies.
    short = await client.get("/api/satellites/25544/conjunctions", params={"hours": 48})
    assert short.status_code == 200
    short_body = short.json()
    assert len(short_body) == 1
    assert short_body[0]["sat_a"]["norad_id"] == 25544
    assert short_body[0]["miss_distance_km"] == 0.42

    # 168h (7d): both qualify, sorted by TCA ascending.
    week = await client.get("/api/satellites/25544/conjunctions", params={"hours": 168})
    assert week.status_code == 200
    week_body = week.json()
    assert len(week_body) == 2
    tcas = [row["tca"] for row in week_body]
    assert tcas == sorted(tcas)
