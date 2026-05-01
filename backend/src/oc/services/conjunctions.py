"""Conjunction screening pipeline.

Given a set of satellites with current TLEs, the pipeline produces predicted
close approaches (conjunctions) over a configurable time horizon.

The screening is split into three tiers:

1. **Perigee/apogee filter** — pairs whose orbits cannot physically intersect
   are discarded based on their osculating altitudes plus a buffer.
2. **Coarse temporal sweep** — both members of every surviving pair are
   propagated on a regular grid (typically one minute). Intervals where the
   distance falls below a threshold become candidates.
3. **Refinement** — each candidate interval is searched on a fine grid (one
   second by default) and the time of closest approach (TCA) is refined with
   :func:`scipy.optimize.minimize_scalar` to sub-second precision.

The probability column is a placeholder Gaussian on the miss distance — useful
as a screening proxy, never as an operational PoC value.
"""

from __future__ import annotations

import math
import uuid
from collections.abc import Iterable, Sequence
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta

import numpy as np
import structlog
from scipy.optimize import minimize_scalar
from sgp4.api import Satrec

from oc.services.propagation import (
    Ephemeris,
    orbital_elements,
    propagate,
    propagate_single,
    satrec_from_tle,
)

logger = structlog.get_logger(__name__)


@dataclass(frozen=True)
class SatelliteState:
    """Container linking a satellite's identifiers and its propagator."""

    norad_id: int
    name: str
    line1: str
    line2: str
    satrec: Satrec = field(repr=False)
    tle_db_id: int | None = None

    @classmethod
    def from_tle(
        cls,
        norad_id: int,
        name: str,
        line1: str,
        line2: str,
        tle_db_id: int | None = None,
    ) -> SatelliteState:
        """Build a :class:`SatelliteState` and pre-construct its Satrec."""
        return cls(
            norad_id=norad_id,
            name=name,
            line1=line1,
            line2=line2,
            tle_db_id=tle_db_id,
            satrec=satrec_from_tle(line1, line2),
        )


@dataclass(frozen=True)
class ConjunctionEvent:
    """A single screened close approach."""

    id: str
    sat_a: SatelliteState
    sat_b: SatelliteState
    tca: datetime
    miss_distance_km: float
    relative_velocity_km_s: float
    probability: float


def perigee_apogee_compatible(
    a: SatelliteState, b: SatelliteState, buffer_km: float = 50.0
) -> bool:
    """Return ``True`` if the orbits' altitude ranges overlap within ``buffer_km``.

    This is the cheapest filter: it rejects pairs whose orbital shells cannot
    physically intersect because their (perigee, apogee) altitude bands are
    disjoint by more than ``buffer_km``.
    """
    _, peri_a, apo_a = orbital_elements(a.satrec)
    _, peri_b, apo_b = orbital_elements(b.satrec)
    # Orbits can encounter only if [peri, apo] intervals overlap.
    overlap_low = max(peri_a, peri_b)
    overlap_high = min(apo_a, apo_b)
    return overlap_low - overlap_high <= buffer_km


def _build_time_grid(start: datetime, end: datetime, step_seconds: float) -> list[datetime]:
    """Return an inclusive UTC time grid from ``start`` to ``end``."""
    if end <= start:
        raise ValueError("end must be after start")
    total = (end - start).total_seconds()
    n = math.floor(total / step_seconds) + 1
    return [
        start + timedelta(seconds=i * step_seconds)
        for i in range(n + 1)
        if i * step_seconds <= total + 1e-9
    ]


@dataclass(frozen=True)
class CandidateInterval:
    """A coarse time window where two satellites came within the threshold."""

    start_index: int
    end_index: int
    start_time: datetime
    end_time: datetime
    min_distance_km: float


def coarse_sweep(
    eph_a: Ephemeris,
    eph_b: Ephemeris,
    threshold_km: float,
) -> list[CandidateInterval]:
    """Identify intervals where the two ephemerides are within ``threshold_km``.

    The two ephemerides must share an identical time grid.
    """
    if eph_a.times != eph_b.times:
        raise ValueError("ephemerides must share the same time grid")
    if len(eph_a.times) == 0:
        return []

    diff = eph_a.positions - eph_b.positions
    distances = np.linalg.norm(diff, axis=1)
    below = distances < threshold_km
    if not np.any(below):
        return []

    intervals: list[CandidateInterval] = []
    in_interval = False
    start_idx = 0
    for i, flag in enumerate(below):
        if flag and not in_interval:
            in_interval = True
            start_idx = i
        elif not flag and in_interval:
            in_interval = False
            end_idx = i  # exclusive end on the False sample
            intervals.append(
                CandidateInterval(
                    start_index=max(start_idx - 1, 0),
                    end_index=min(end_idx, len(eph_a.times) - 1),
                    start_time=eph_a.times[max(start_idx - 1, 0)],
                    end_time=eph_a.times[min(end_idx, len(eph_a.times) - 1)],
                    min_distance_km=float(distances[start_idx:end_idx].min()),
                )
            )
    if in_interval:
        end_idx = len(below) - 1
        intervals.append(
            CandidateInterval(
                start_index=max(start_idx - 1, 0),
                end_index=end_idx,
                start_time=eph_a.times[max(start_idx - 1, 0)],
                end_time=eph_a.times[end_idx],
                min_distance_km=float(distances[start_idx : end_idx + 1].min()),
            )
        )
    return intervals


def _distance_at(satrec_a: Satrec, satrec_b: Satrec, t_seconds: float, t0: datetime) -> float:
    """Distance (km) at ``t0 + t_seconds`` between the two satellites."""
    when = t0 + timedelta(seconds=t_seconds)
    r_a, _ = propagate_single(satrec_a, when)
    r_b, _ = propagate_single(satrec_b, when)
    return float(np.linalg.norm(r_a - r_b))


def refine_tca(
    sat_a: SatelliteState,
    sat_b: SatelliteState,
    interval: CandidateInterval,
    fine_step_seconds: float = 1.0,
) -> tuple[datetime, float, float]:
    """Refine the time of closest approach inside ``interval``.

    Returns:
        A tuple ``(tca, miss_distance_km, relative_velocity_km_s)``. The TCA
        is timezone-aware UTC; the relative velocity is the magnitude of the
        difference of the velocity vectors at the TCA.
    """
    t0 = interval.start_time
    span = (interval.end_time - interval.start_time).total_seconds()
    n_fine = max(math.ceil(span / fine_step_seconds) + 1, 3)
    fine_times = [t0 + timedelta(seconds=i * span / (n_fine - 1)) for i in range(n_fine)]
    eph_a = propagate(sat_a.satrec, fine_times)
    eph_b = propagate(sat_b.satrec, fine_times)
    distances = np.linalg.norm(eph_a.positions - eph_b.positions, axis=1)
    best_idx = int(np.argmin(distances))

    # Bracket for parabolic refinement.
    lo = max(best_idx - 1, 0)
    hi = min(best_idx + 1, n_fine - 1)
    bracket_lo = (fine_times[lo] - t0).total_seconds()
    bracket_hi = (fine_times[hi] - t0).total_seconds()

    def objective(t_seconds: float) -> float:
        return _distance_at(sat_a.satrec, sat_b.satrec, t_seconds, t0)

    if bracket_hi <= bracket_lo:
        # Degenerate window — return the best discrete sample.
        tca_offset = (fine_times[best_idx] - t0).total_seconds()
    else:
        result = minimize_scalar(
            objective,
            bounds=(bracket_lo, bracket_hi),
            method="bounded",
            options={"xatol": 1e-3},
        )
        tca_offset = float(result.x)

    tca = t0 + timedelta(seconds=tca_offset)
    r_a, v_a = propagate_single(sat_a.satrec, tca)
    r_b, v_b = propagate_single(sat_b.satrec, tca)
    miss = float(np.linalg.norm(r_a - r_b))
    rel_vel = float(np.linalg.norm(v_a - v_b))
    if tca.tzinfo is None:
        tca = tca.replace(tzinfo=UTC)
    return tca, miss, rel_vel


def screening_probability(miss_km: float, sigma_km: float = 1.0) -> float:
    """Placeholder probability proxy for screening.

    Computes ``exp(-miss_km^2 / (2 * sigma_km^2))``. This is **not** an
    operational probability of collision (PoC); it is a monotonically
    decreasing screening indicator suitable for sorting and triage.
    """
    if sigma_km <= 0.0:
        raise ValueError("sigma_km must be positive")
    return float(math.exp(-(miss_km**2) / (2.0 * sigma_km**2)))


def _generate_id() -> str:
    """Return a fresh hex id for a conjunction row."""
    return uuid.uuid4().hex


def screen_pair(
    sat_a: SatelliteState,
    sat_b: SatelliteState,
    start: datetime,
    end: datetime,
    coarse_step_seconds: float = 60.0,
    fine_step_seconds: float = 1.0,
    perigee_apogee_buffer_km: float = 50.0,
    distance_threshold_km: float = 50.0,
    probability_sigma_km: float = 1.0,
) -> list[ConjunctionEvent]:
    """Screen one pair of satellites and return refined events."""
    if sat_a.norad_id == sat_b.norad_id:
        return []
    if not perigee_apogee_compatible(sat_a, sat_b, buffer_km=perigee_apogee_buffer_km):
        return []

    grid = _build_time_grid(start, end, coarse_step_seconds)
    eph_a = propagate(sat_a.satrec, grid)
    eph_b = propagate(sat_b.satrec, grid)
    intervals = coarse_sweep(eph_a, eph_b, distance_threshold_km)
    events: list[ConjunctionEvent] = []
    for interval in intervals:
        tca, miss, rel_vel = refine_tca(sat_a, sat_b, interval, fine_step_seconds)
        if miss > distance_threshold_km:
            continue
        events.append(
            ConjunctionEvent(
                id=_generate_id(),
                sat_a=sat_a,
                sat_b=sat_b,
                tca=tca,
                miss_distance_km=miss,
                relative_velocity_km_s=rel_vel,
                probability=screening_probability(miss, probability_sigma_km),
            )
        )
    return events


def screen_population(
    satellites: Sequence[SatelliteState],
    start: datetime,
    end: datetime,
    coarse_step_seconds: float = 60.0,
    fine_step_seconds: float = 1.0,
    perigee_apogee_buffer_km: float = 50.0,
    distance_threshold_km: float = 50.0,
    probability_sigma_km: float = 1.0,
    max_pairs: int | None = None,
) -> list[ConjunctionEvent]:
    """Run the full three-tier screen across every distinct pair.

    Args:
        satellites: Population to screen.
        start: Lower bound of the time window (UTC).
        end: Upper bound of the time window (UTC).
        max_pairs: Optional safety cap on the number of pairs evaluated.

    Returns:
        A list of :class:`ConjunctionEvent` sorted by ``miss_distance_km``.
    """
    events: list[ConjunctionEvent] = []
    examined = 0
    for i in range(len(satellites)):
        for j in range(i + 1, len(satellites)):
            if max_pairs is not None and examined >= max_pairs:
                logger.warning("max_pairs limit reached", limit=max_pairs, returning=len(events))
                return sorted(events, key=lambda e: e.miss_distance_km)
            examined += 1
            try:
                pair_events = screen_pair(
                    satellites[i],
                    satellites[j],
                    start,
                    end,
                    coarse_step_seconds=coarse_step_seconds,
                    fine_step_seconds=fine_step_seconds,
                    perigee_apogee_buffer_km=perigee_apogee_buffer_km,
                    distance_threshold_km=distance_threshold_km,
                    probability_sigma_km=probability_sigma_km,
                )
            except Exception as exc:
                logger.warning(
                    "pair screening failed",
                    sat_a=satellites[i].norad_id,
                    sat_b=satellites[j].norad_id,
                    error=str(exc),
                )
                continue
            events.extend(pair_events)
    return sorted(events, key=lambda e: e.miss_distance_km)


def states_from_records(
    records: Iterable[tuple[int, str, str, str, int | None]],
) -> list[SatelliteState]:
    """Helper for callers loading ``(norad_id, name, line1, line2, tle_id)`` rows."""
    return [
        SatelliteState.from_tle(
            norad_id=norad_id,
            name=name,
            line1=line1,
            line2=line2,
            tle_db_id=tle_id,
        )
        for norad_id, name, line1, line2, tle_id in records
    ]
