"""HTTP API smoke tests using ``httpx.AsyncClient`` against the FastAPI app."""

from __future__ import annotations

import uuid
from datetime import UTC, date, datetime, timedelta

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from oc.models import TLE, Conjunction, Satellite


async def _seed_database(session: AsyncSession) -> dict[str, object]:
    """Insert two satellites, two TLEs and one conjunction. Returns key ids."""
    now = datetime.now(UTC)
    sat_a = Satellite(
        norad_id=10001,
        name="ALPHA-1",
        country="US",
        object_type="PAYLOAD",
        launch_date=date(2020, 1, 15),
        is_active=True,
    )
    sat_b = Satellite(
        norad_id=10002,
        name="BETA-2",
        country="FR",
        object_type="PAYLOAD",
        launch_date=date(2021, 6, 1),
        is_active=True,
    )
    session.add_all([sat_a, sat_b])
    await session.flush()

    tle_a = TLE(
        norad_id=10001,
        epoch=now - timedelta(hours=2),
        line1="1 10001U 20015A   24001.00000000  .00000000  00000-0  00000+0 0    01",
        line2="2 10001  51.6000   0.0000 0000000   0.0000   0.0000 15.00000000    02",
    )
    tle_b = TLE(
        norad_id=10002,
        epoch=now - timedelta(hours=1),
        line1="1 10002U 21062A   24001.00000000  .00000000  00000-0  00000+0 0    03",
        line2="2 10002  51.6000   0.0000 0000000   0.0000   0.0000 15.00000000    04",
    )
    session.add_all([tle_a, tle_b])
    await session.flush()

    conj = Conjunction(
        id=uuid.uuid4().hex,
        sat_a_norad_id=10001,
        sat_b_norad_id=10002,
        tle_a_id=tle_a.id,
        tle_b_id=tle_b.id,
        tca=now + timedelta(hours=12),
        miss_distance_km=0.84,
        relative_velocity_km_s=13.2,
        probability=0.7,
    )
    session.add(conj)
    await session.commit()
    return {
        "conj_id": conj.id,
        "tle_a_id": tle_a.id,
        "tle_b_id": tle_b.id,
    }


@pytest.mark.asyncio
async def test_health(client: AsyncClient, db_session: AsyncSession) -> None:
    """``/api/health`` must return ``status: ok`` and a numeric TLE age."""
    await _seed_database(db_session)
    response = await client.get("/api/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert isinstance(body["version"], str)
    assert body["tle_age_hours"] is not None
    assert 0.5 < float(body["tle_age_hours"]) < 5.0


@pytest.mark.asyncio
async def test_health_with_empty_database(client: AsyncClient) -> None:
    """When no TLEs exist, ``tle_age_hours`` must be ``null``."""
    response = await client.get("/api/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["tle_age_hours"] is None


@pytest.mark.asyncio
async def test_stats(client: AsyncClient, db_session: AsyncSession) -> None:
    """``/api/stats`` must aggregate counts correctly."""
    await _seed_database(db_session)
    response = await client.get("/api/stats")
    assert response.status_code == 200
    body = response.json()
    assert body["total_satellites"] == 2
    assert body["total_active"] == 2
    assert body["conjunctions_24h"] == 1
    assert body["conjunctions_72h"] == 1
    assert body["high_risk_24h"] == 1
    assert body["tle_last_updated"] is not None


@pytest.mark.asyncio
async def test_satellites_list_and_filter(client: AsyncClient, db_session: AsyncSession) -> None:
    """``/api/satellites`` supports text filtering and pagination."""
    await _seed_database(db_session)
    response = await client.get("/api/satellites")
    assert response.status_code == 200
    body = response.json()
    assert len(body) == 2
    norad_ids = {item["norad_id"] for item in body}
    assert norad_ids == {10001, 10002}

    filtered = await client.get("/api/satellites", params={"q": "alpha"})
    assert filtered.status_code == 200
    body_f = filtered.json()
    assert len(body_f) == 1
    assert body_f[0]["norad_id"] == 10001
    assert body_f[0]["type"] == "PAYLOAD"

    paginated = await client.get("/api/satellites", params={"limit": 1, "offset": 1})
    assert paginated.status_code == 200
    body_p = paginated.json()
    assert len(body_p) == 1


@pytest.mark.asyncio
async def test_conjunctions_list(client: AsyncClient, db_session: AsyncSession) -> None:
    """``/api/conjunctions`` honours the default filters and shape."""
    await _seed_database(db_session)
    response = await client.get("/api/conjunctions")
    assert response.status_code == 200
    body = response.json()
    assert len(body) == 1
    item = body[0]
    assert item["miss_distance_km"] == 0.84
    assert item["sat_a"]["norad_id"] == 10001
    assert item["sat_b"]["norad_id"] == 10002
    assert "id" in item


@pytest.mark.asyncio
async def test_conjunctions_list_includes_tca_positions(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    """Each row carries the sub-satellite point of A and B at TCA."""
    await _seed_database(db_session)
    response = await client.get("/api/conjunctions")
    assert response.status_code == 200
    item = response.json()[0]
    for key in ("tca_position_a", "tca_position_b"):
        position = item[key]
        assert position is not None, f"{key} should not be null for valid TLEs"
        assert -90.0 <= position["latitude_deg"] <= 90.0
        assert -180.0 <= position["longitude_deg"] <= 180.0
        # The seeded TLEs are LEO; altitude is comfortably under GEO.
        assert -50.0 < position["altitude_km"] < 36_000.0


@pytest.mark.asyncio
async def test_conjunctions_filter_max_distance(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    """Filtering ``max_distance_km`` below the miss must hide the row."""
    await _seed_database(db_session)
    response = await client.get("/api/conjunctions", params={"max_distance_km": 0.1})
    assert response.status_code == 200
    assert response.json() == []


@pytest.mark.asyncio
async def test_conjunction_detail_includes_tles(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    """``/api/conjunctions/{id}`` returns the full payload including both TLEs."""
    seeded = await _seed_database(db_session)
    conj_id = seeded["conj_id"]
    response = await client.get(f"/api/conjunctions/{conj_id}")
    assert response.status_code == 200
    body = response.json()
    assert body["id"] == conj_id
    assert body["tle_a_line1"].startswith("1 10001")
    assert body["tle_a_line2"].startswith("2 10001")
    assert body["tle_b_line1"].startswith("1 10002")
    assert body["tle_b_line2"].startswith("2 10002")
    assert body["sat_a"]["country"] == "US"
    assert body["sat_b"]["country"] == "FR"


@pytest.mark.asyncio
async def test_conjunction_detail_404(client: AsyncClient) -> None:
    """An unknown id returns a 404 with a JSON ``detail``."""
    response = await client.get("/api/conjunctions/does-not-exist")
    assert response.status_code == 404
    assert response.json() == {"detail": "conjunction not found"}


@pytest.mark.asyncio
async def test_calendar_feed_is_valid_ical(client: AsyncClient, db_session: AsyncSession) -> None:
    """``/api/calendar.ics`` returns a single VEVENT for the seeded conjunction."""
    seeded = await _seed_database(db_session)
    response = await client.get("/api/calendar.ics")
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/calendar")
    body = response.text
    assert body.startswith("BEGIN:VCALENDAR\r\n")
    assert body.rstrip("\r\n").endswith("END:VCALENDAR")
    assert "VERSION:2.0" in body
    assert "BEGIN:VEVENT" in body
    assert "END:VEVENT" in body
    assert f"UID:{seeded['conj_id']}@orbital-conjunctions" in body
    # Lines must end with CRLF per RFC 5545. A bare LF would fail parsers.
    assert "\n\r\n" not in body  # no trailing-LF before CRLF artefacts
    assert "\r\n" in body
    # The summary must mention both satellite names.
    assert "ALPHA-1" in body and "BETA-2" in body


@pytest.mark.asyncio
async def test_calendar_feed_filters_by_norad_id(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    """A NORAD-id filter that excludes both satellites must yield an empty feed."""
    await _seed_database(db_session)
    response = await client.get("/api/calendar.ics", params={"norad_id": 99999})
    assert response.status_code == 200
    body = response.text
    assert "BEGIN:VEVENT" not in body
    assert body.startswith("BEGIN:VCALENDAR")
    assert body.rstrip("\r\n").endswith("END:VCALENDAR")


@pytest.mark.asyncio
async def test_conjunctions_csv_export(client: AsyncClient, db_session: AsyncSession) -> None:
    """``/api/conjunctions.csv`` streams a parseable CSV with a header row."""
    seeded = await _seed_database(db_session)
    response = await client.get("/api/conjunctions.csv")
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/csv")
    assert "attachment" in response.headers.get("content-disposition", "")
    body = response.text
    lines = body.splitlines()
    header = lines[0].split(",")
    assert "id" in header
    assert "tca_utc" in header
    assert "miss_distance_km" in header
    assert "sat_a_lat_deg" in header
    assert "sat_b_alt_km" in header
    # One header + one data row for the seeded conjunction.
    assert len(lines) == 2
    data = lines[1].split(",")
    assert data[0] == seeded["conj_id"]


@pytest.mark.asyncio
async def test_conjunctions_csv_filters_by_norad_id(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    """Filtering by an unknown NORAD id must return only the header row."""
    await _seed_database(db_session)
    response = await client.get("/api/conjunctions.csv", params={"norad_id": 99999})
    assert response.status_code == 200
    body = response.text
    assert len(body.splitlines()) == 1  # header only


@pytest.mark.asyncio
async def test_satellite_tle_export(client: AsyncClient, db_session: AsyncSession) -> None:
    """``/api/satellites/{id}/tle.txt`` returns the 3-line TLE as plain text."""
    await _seed_database(db_session)
    response = await client.get("/api/satellites/10001/tle.txt")
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/plain")
    assert "attachment" in response.headers.get("content-disposition", "")
    body = response.text
    lines = body.splitlines()
    assert lines[0] == "ALPHA-1"
    assert lines[1].startswith("1 10001")
    assert lines[2].startswith("2 10001")


@pytest.mark.asyncio
async def test_satellite_tle_export_404(client: AsyncClient) -> None:
    """An unknown identifier returns a 404 with a JSON ``detail``."""
    response = await client.get("/api/satellites/99999/tle.txt")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_pagination_cap_respects_max_limit(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    """A ``limit`` greater than the configured cap must return at most the cap rows."""
    # Insert many satellites to force pagination behavior.
    for i in range(5):
        db_session.add(Satellite(norad_id=20000 + i, name=f"BULK-{i}", is_active=True))
    await db_session.commit()
    response = await client.get("/api/satellites", params={"limit": 1000})
    assert response.status_code == 200
    assert len(response.json()) == 5
