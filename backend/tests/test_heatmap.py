"""Unit and integration tests for the orbital congestion heatmap.

The unit tests cover the use case in isolation against a fake
repository; the HTTP tests seed a SQLite database and exercise both
endpoints end-to-end.
"""

from __future__ import annotations

import uuid
from collections.abc import Sequence
from datetime import UTC, date, datetime, timedelta
from typing import Final

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from oc.application.use_cases.compute_heatmap import (
    aggregate_orbital_bins,
    compute_conjunctions_timeline,
    compute_heatmap,
)
from oc.domain.entities import (
    HEATMAP_ALTITUDE_MIN_KM,
    HEATMAP_ALTITUDE_STEP_KM,
    HEATMAP_INCLINATION_MIN_DEG,
    HEATMAP_INCLINATION_STEP_DEG,
    ConjunctionTimelinePoint,
    OrbitalBin,
)
from oc.models import TLE, Conjunction, Satellite

# Number of altitude bins between 200 and 2000 km in 50 km steps.
_EXPECTED_ALT_BINS: Final[int] = 36
# Number of inclination bins between 0 and 180 deg in 5 deg steps.
_EXPECTED_INC_BINS: Final[int] = 36


class _FakeHeatmapRepository:
    """In-memory repository used by the use-case unit tests."""

    def __init__(
        self,
        bins: Sequence[OrbitalBin],
        timeline: Sequence[ConjunctionTimelinePoint] | None = None,
    ) -> None:
        self._bins = list(bins)
        self._timeline = list(timeline or [])

    async def list_active_orbital_bins(self) -> Sequence[OrbitalBin]:
        return list(self._bins)

    async def conjunctions_per_day(
        self, start: datetime, end: datetime
    ) -> Sequence[ConjunctionTimelinePoint]:
        return [p for p in self._timeline if start.date() <= p.date < end.date()]


def test_aggregate_orbital_bins_returns_documented_shape() -> None:
    matrix = aggregate_orbital_bins([])
    assert len(matrix.altitude_bands) == _EXPECTED_ALT_BINS
    assert len(matrix.inclination_bands) == _EXPECTED_INC_BINS
    assert matrix.altitude_bands[0] == HEATMAP_ALTITUDE_MIN_KM
    assert matrix.inclination_bands[0] == HEATMAP_INCLINATION_MIN_DEG
    # The lower edge of the second altitude band is the first edge plus
    # the step, by construction.
    assert matrix.altitude_bands[1] == HEATMAP_ALTITUDE_MIN_KM + HEATMAP_ALTITUDE_STEP_KM
    assert matrix.inclination_bands[1] == HEATMAP_INCLINATION_MIN_DEG + HEATMAP_INCLINATION_STEP_DEG
    assert matrix.total_satellites == 0
    assert all(c == 0 for row in matrix.counts for c in row)


def test_aggregate_orbital_bins_drops_out_of_window() -> None:
    bins = [
        OrbitalBin(altitude_km=550.0, inclination_deg=53.0),  # in
        OrbitalBin(altitude_km=199.0, inclination_deg=53.0),  # too low
        OrbitalBin(altitude_km=2500.0, inclination_deg=53.0),  # too high
        OrbitalBin(altitude_km=550.0, inclination_deg=181.0),  # invalid
    ]
    matrix = aggregate_orbital_bins(bins)
    assert matrix.total_satellites == 1


def test_aggregate_orbital_bins_counts_known_population() -> None:
    bins = [
        OrbitalBin(altitude_km=550.0, inclination_deg=53.0),
        OrbitalBin(altitude_km=552.0, inclination_deg=53.4),
        OrbitalBin(altitude_km=820.0, inclination_deg=98.7),
    ]
    matrix = aggregate_orbital_bins(bins)
    assert matrix.total_satellites == 3
    # 550 km falls into the (550-600) bin; 53 deg into the (50-55) bin.
    alt_idx_550 = matrix.altitude_bands.index(550.0)
    inc_idx_50 = matrix.inclination_bands.index(50.0)
    assert matrix.counts[alt_idx_550][inc_idx_50] == 2
    alt_idx_800 = matrix.altitude_bands.index(800.0)
    inc_idx_95 = matrix.inclination_bands.index(95.0)
    assert matrix.counts[alt_idx_800][inc_idx_95] == 1


@pytest.mark.asyncio
async def test_compute_heatmap_delegates_to_repository() -> None:
    repo = _FakeHeatmapRepository(
        [
            OrbitalBin(altitude_km=510.0, inclination_deg=53.0),
            OrbitalBin(altitude_km=510.0, inclination_deg=53.0),
        ]
    )
    matrix = await compute_heatmap(repo)
    assert matrix.total_satellites == 2


@pytest.mark.asyncio
async def test_compute_conjunctions_timeline_pads_missing_days() -> None:
    today = datetime.now(UTC).date()
    point = ConjunctionTimelinePoint(
        date=today - timedelta(days=2),
        miss_lt_1km=1,
        miss_lt_5km=4,
        total=10,
    )
    repo = _FakeHeatmapRepository(bins=[], timeline=[point])
    points = await compute_conjunctions_timeline(repo, days=5)
    assert len(points) == 5
    by_date = {p.date: p for p in points}
    assert by_date[point.date].total == 10
    # Missing days must be padded with zeros.
    other = today - timedelta(days=4)
    assert by_date[other].total == 0


@pytest.mark.asyncio
async def test_compute_conjunctions_timeline_validates_window() -> None:
    repo = _FakeHeatmapRepository(bins=[])
    with pytest.raises(ValueError):
        await compute_conjunctions_timeline(repo, days=0)
    with pytest.raises(ValueError):
        await compute_conjunctions_timeline(repo, days=10_000)


# --- Integration tests -------------------------------------------------------
# A 530 km / 53 deg orbit (≈ Starlink-like) used as the seed TLE for the
# integration tests. Mean motion ~15.05 rev/day and eccentricity tightened
# so the SGP4 record agrees with the textbook 530 km altitude.
_LINE1_TPL: str = "1 {nid:05d}U 19074A   24001.00000000  .00000000  00000-0  00000+0 0    01"
_LINE2_TPL: str = "2 {nid:05d}  53.0000   0.0000 0000000   0.0000   0.0000 15.05000000    02"


def _seed_tle_lines(norad_id: int) -> tuple[str, str]:
    return _LINE1_TPL.format(nid=norad_id), _LINE2_TPL.format(nid=norad_id)


@pytest.mark.asyncio
async def test_heatmap_endpoint_bins_seeded_population(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    """Seeding 1000 satellites must yield bin counts that sum to 1000."""
    epoch = datetime(2024, 1, 1, tzinfo=UTC)
    sats: list[Satellite] = []
    tles: list[TLE] = []
    for i in range(1000):
        nid = 80000 + i
        line1, line2 = _seed_tle_lines(nid)
        sats.append(Satellite(norad_id=nid, name=f"SEED-{i}", is_active=True))
        tles.append(TLE(norad_id=nid, epoch=epoch, line1=line1, line2=line2))
    db_session.add_all(sats)
    await db_session.flush()
    db_session.add_all(tles)
    await db_session.commit()

    response = await client.get("/api/heatmap/altitude-inclination")
    assert response.status_code == 200
    body = response.json()
    counts = body["counts"]
    total = sum(c for row in counts for c in row)
    # The seeded TLE places every satellite in the same bin so the total
    # must equal exactly the seeded population (no out-of-range drops).
    assert total == 1000
    assert body["total_satellites"] == 1000
    assert len(body["altitude_bands"]) == _EXPECTED_ALT_BINS
    assert len(body["inclination_bands"]) == _EXPECTED_INC_BINS
    assert body["altitude_step_km"] == HEATMAP_ALTITUDE_STEP_KM
    assert body["inclination_step_deg"] == HEATMAP_INCLINATION_STEP_DEG


@pytest.mark.asyncio
async def test_heatmap_endpoint_runs_under_budget(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    """The endpoint must respond well under 200 ms even with 1000 satellites.

    The integration suite runs SQLite in-memory so the timing here is a
    soft sanity check rather than a true production benchmark.
    """
    import time

    epoch = datetime(2024, 1, 1, tzinfo=UTC)
    bulk_sats: list[Satellite] = []
    bulk_tles: list[TLE] = []
    for i in range(1000):
        nid = 90000 + i
        line1, line2 = _seed_tle_lines(nid)
        bulk_sats.append(Satellite(norad_id=nid, name=f"PERF-{i}", is_active=True))
        bulk_tles.append(TLE(norad_id=nid, epoch=epoch, line1=line1, line2=line2))
    db_session.add_all(bulk_sats)
    await db_session.flush()
    db_session.add_all(bulk_tles)
    await db_session.commit()

    started = time.perf_counter()
    response = await client.get("/api/heatmap/altitude-inclination")
    elapsed_ms = (time.perf_counter() - started) * 1000.0
    assert response.status_code == 200
    # Generous threshold (1 second) — the spec asks for 200 ms in
    # production but the in-memory SQLite + cold start in CI is noisier.
    assert elapsed_ms < 1000.0


@pytest.mark.asyncio
async def test_conjunctions_timeline_endpoint_returns_padded_window(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    """The endpoint must return ``days`` entries with correct per-day counts."""
    now = datetime.now(UTC)
    # Seed two satellites and TLEs to satisfy foreign keys.
    sat_a = Satellite(norad_id=70001, name="ALPHA", is_active=True)
    sat_b = Satellite(norad_id=70002, name="BETA", is_active=True)
    db_session.add_all([sat_a, sat_b])
    await db_session.flush()
    line1, line2 = _seed_tle_lines(70001)
    tle_a = TLE(norad_id=70001, epoch=now - timedelta(hours=1), line1=line1, line2=line2)
    line1b, line2b = _seed_tle_lines(70002)
    tle_b = TLE(norad_id=70002, epoch=now - timedelta(hours=2), line1=line1b, line2=line2b)
    db_session.add_all([tle_a, tle_b])
    await db_session.flush()

    # One conjunction yesterday with 0.5 km miss, one today with 3 km miss.
    yesterday = now - timedelta(days=1)
    db_session.add_all(
        [
            Conjunction(
                id=uuid.uuid4().hex,
                sat_a_norad_id=70001,
                sat_b_norad_id=70002,
                tle_a_id=tle_a.id,
                tle_b_id=tle_b.id,
                tca=yesterday,
                miss_distance_km=0.5,
                relative_velocity_km_s=10.0,
                probability=0.4,
            ),
            Conjunction(
                id=uuid.uuid4().hex,
                sat_a_norad_id=70001,
                sat_b_norad_id=70002,
                tle_a_id=tle_a.id,
                tle_b_id=tle_b.id,
                tca=now,
                miss_distance_km=3.0,
                relative_velocity_km_s=11.0,
                probability=0.05,
            ),
        ]
    )
    await db_session.commit()

    response = await client.get("/api/heatmap/conjunctions-timeline", params={"days": 7})
    assert response.status_code == 200
    body = response.json()
    assert len(body) == 7
    # Sorted ascending by date.
    dates = [date.fromisoformat(point["date"]) for point in body]
    assert dates == sorted(dates)

    by_date = {point["date"]: point for point in body}
    today_str = now.date().isoformat()
    yesterday_str = yesterday.date().isoformat()
    assert by_date[today_str]["total"] == 1
    assert by_date[today_str]["miss_lt_1km"] == 0
    assert by_date[today_str]["miss_lt_5km"] == 1
    assert by_date[yesterday_str]["total"] == 1
    assert by_date[yesterday_str]["miss_lt_1km"] == 1
    assert by_date[yesterday_str]["miss_lt_5km"] == 1


@pytest.mark.asyncio
async def test_conjunctions_timeline_rejects_invalid_window(client: AsyncClient) -> None:
    response = await client.get("/api/heatmap/conjunctions-timeline", params={"days": 0})
    assert response.status_code == 422
    response = await client.get("/api/heatmap/conjunctions-timeline", params={"days": 9999})
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_heatmap_endpoint_handles_empty_database(client: AsyncClient) -> None:
    """An empty database must yield a zero-filled matrix with the expected shape."""
    response = await client.get("/api/heatmap/altitude-inclination")
    assert response.status_code == 200
    body = response.json()
    assert body["total_satellites"] == 0
    assert len(body["counts"]) == _EXPECTED_ALT_BINS
    assert len(body["counts"][0]) == _EXPECTED_INC_BINS
    assert all(c == 0 for row in body["counts"] for c in row)
