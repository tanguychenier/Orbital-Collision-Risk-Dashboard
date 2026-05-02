"""Heatmap aggregation use case.

The ``orbital congestion heatmap`` is a 2D matrix of satellite counts
binned by altitude (rows, 50 km steps in ``[200, 2000]`` km) and
inclination (columns, 5 degree steps in ``[0, 180]``). The use case sits
strictly in the application layer: it depends on a repository port and
returns framework-agnostic dataclasses. The HTTP adapter is responsible
for serialising the result.

The companion ``compute_conjunctions_timeline`` use case wraps the
day-bucket aggregation exposed by the same repository port. It exists in
this module so the two heatmap-flavoured use cases live next to each
other.
"""

from __future__ import annotations

import math
from collections.abc import Iterable
from datetime import UTC, date, datetime, timedelta

from oc.application.ports import Clock, HeatmapRepository
from oc.domain.entities import (
    HEATMAP_ALTITUDE_MAX_KM,
    HEATMAP_ALTITUDE_MIN_KM,
    HEATMAP_ALTITUDE_STEP_KM,
    HEATMAP_INCLINATION_MAX_DEG,
    HEATMAP_INCLINATION_MIN_DEG,
    HEATMAP_INCLINATION_STEP_DEG,
    ConjunctionTimelinePoint,
    HeatmapMatrix,
    OrbitalBin,
)

# Defensive defaults exposed for callers that want to override the binning
# (the test-suite uses these to assert the matrix shape is exactly what
# the public API documents).
_DEFAULT_ALT_MIN = HEATMAP_ALTITUDE_MIN_KM
_DEFAULT_ALT_MAX = HEATMAP_ALTITUDE_MAX_KM
_DEFAULT_ALT_STEP = HEATMAP_ALTITUDE_STEP_KM
_DEFAULT_INC_MIN = HEATMAP_INCLINATION_MIN_DEG
_DEFAULT_INC_MAX = HEATMAP_INCLINATION_MAX_DEG
_DEFAULT_INC_STEP = HEATMAP_INCLINATION_STEP_DEG


def _band_edges(start: float, stop: float, step: float) -> tuple[float, ...]:
    """Return the inclusive lower edges of the bins in ``[start, stop)``.

    The last bin's upper edge is ``start + step * len(edges)`` and is
    used by :func:`_bin_index` to discard out-of-range entries.
    """
    if step <= 0.0:
        raise ValueError("step must be positive")
    if stop <= start:
        raise ValueError("stop must be strictly greater than start")
    n = math.ceil((stop - start) / step)
    return tuple(start + i * step for i in range(n))


def _bin_index(value: float, lower: float, step: float, n_bins: int) -> int | None:
    """Return the bin index for ``value``.

    Returns ``None`` if ``value`` falls outside
    ``[lower, lower + step * n_bins)``.
    """
    if value < lower:
        return None
    idx = math.floor((value - lower) / step)
    if idx < 0 or idx >= n_bins:
        return None
    return idx


def aggregate_orbital_bins(
    bins: Iterable[OrbitalBin],
    *,
    altitude_min_km: float = _DEFAULT_ALT_MIN,
    altitude_max_km: float = _DEFAULT_ALT_MAX,
    altitude_step_km: float = _DEFAULT_ALT_STEP,
    inclination_min_deg: float = _DEFAULT_INC_MIN,
    inclination_max_deg: float = _DEFAULT_INC_MAX,
    inclination_step_deg: float = _DEFAULT_INC_STEP,
) -> HeatmapMatrix:
    """Bucket a stream of :class:`OrbitalBin` into a 2D :class:`HeatmapMatrix`.

    Out-of-range entries (altitude outside the LEO window or inclination
    outside ``[0, 180]``) are silently dropped so the matrix shape remains
    deterministic regardless of the input population.
    """
    altitude_bands = _band_edges(altitude_min_km, altitude_max_km, altitude_step_km)
    inclination_bands = _band_edges(inclination_min_deg, inclination_max_deg, inclination_step_deg)
    n_alt = len(altitude_bands)
    n_inc = len(inclination_bands)
    counts: list[list[int]] = [[0 for _ in range(n_inc)] for _ in range(n_alt)]
    total = 0
    for entry in bins:
        i = _bin_index(entry.altitude_km, altitude_min_km, altitude_step_km, n_alt)
        j = _bin_index(entry.inclination_deg, inclination_min_deg, inclination_step_deg, n_inc)
        if i is None or j is None:
            continue
        counts[i][j] += 1
        total += 1
    return HeatmapMatrix(
        altitude_bands=altitude_bands,
        inclination_bands=inclination_bands,
        counts=tuple(tuple(row) for row in counts),
        total_satellites=total,
    )


async def compute_heatmap(repository: HeatmapRepository) -> HeatmapMatrix:
    """Build a fresh altitude-vs-inclination heatmap from the repository.

    The use case has no domain-specific logic of its own beyond
    delegating to :func:`aggregate_orbital_bins`. It exists as a thin
    application-layer entry point so the HTTP adapter never imports a
    persistence module directly.
    """
    bins = await repository.list_active_orbital_bins()
    return aggregate_orbital_bins(bins)


def _utcnow() -> datetime:
    """Return a timezone-aware UTC ``datetime`` (overridable in tests)."""
    return datetime.now(UTC)


def _start_of_day_utc(when: datetime) -> datetime:
    """Return the UTC midnight at the start of ``when``'s calendar day."""
    aware = when if when.tzinfo is not None else when.replace(tzinfo=UTC)
    return datetime(aware.year, aware.month, aware.day, tzinfo=UTC)


def _fill_missing_days(
    points: Iterable[ConjunctionTimelinePoint],
    start_day: date,
    end_day: date,
) -> tuple[ConjunctionTimelinePoint, ...]:
    """Pad ``points`` with zero-count entries for any missing day in ``[start, end]``."""
    by_day = {p.date: p for p in points}
    out: list[ConjunctionTimelinePoint] = []
    cursor = start_day
    while cursor <= end_day:
        out.append(
            by_day.get(
                cursor,
                ConjunctionTimelinePoint(
                    date=cursor,
                    miss_lt_1km=0,
                    miss_lt_5km=0,
                    total=0,
                ),
            )
        )
        cursor = cursor + timedelta(days=1)
    return tuple(out)


# Cap the timeline window to keep the response payload predictable. A
# month is more than enough for a daily-resolution chart and matches the
# default the dashboard surface offers.
_MAX_TIMELINE_DAYS: int = 365


async def compute_conjunctions_timeline(
    repository: HeatmapRepository,
    days: int,
    *,
    clock: Clock | None = None,
) -> tuple[ConjunctionTimelinePoint, ...]:
    """Aggregate ``conjunctions`` per UTC day over the past ``days`` days.

    The window is closed at the start of *tomorrow* so the current day is
    included in the result. The repository is free to return entries in
    any order; the use case sorts ascending by date and pads missing days
    with zeros.
    """
    if days <= 0:
        raise ValueError("days must be positive")
    if days > _MAX_TIMELINE_DAYS:
        raise ValueError(f"days must be <= {_MAX_TIMELINE_DAYS}")
    now = clock.now() if clock is not None else _utcnow()
    end = _start_of_day_utc(now) + timedelta(days=1)
    start = end - timedelta(days=days)
    points = await repository.conjunctions_per_day(start, end)
    padded = _fill_missing_days(points, start.date(), end.date() - timedelta(days=1))
    return tuple(sorted(padded, key=lambda p: p.date))
