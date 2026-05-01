"""Conjunction screening use case.

The screening pipeline produces predicted close approaches for every
satellite pair in a given population. It is split into three tiers:

1. **Perigee/apogee filter** -- pairs whose orbital shells cannot
   physically intersect are discarded based on their osculating
   altitudes plus a safety buffer.
2. **Coarse temporal sweep** -- both members of every surviving pair are
   propagated on a regular grid (typically one minute). Intervals where
   the inter-satellite distance falls below a threshold become
   candidates.
3. **Refinement** -- each candidate interval is re-sampled on a fine
   grid (one second by default) and the time of closest approach (TCA)
   is refined with a bracketed bounded minimizer to sub-second precision.

The probability column is a placeholder Gaussian on the miss distance --
useful as a screening proxy, never as an operational PoC value.
"""

from __future__ import annotations

import logging
import math
import uuid
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

import numpy as np

from oc.application.ports import BoundedScalarMinimizer, Propagator
from oc.domain.entities import ConjunctionEvent, SatelliteState
from oc.domain.value_objects import CandidateInterval, Ephemeris

logger = logging.getLogger(__name__)

# --- Algorithmic constants ---------------------------------------------------
# Floating-point slack used when checking that the last grid sample fits
# inside the requested time window. Anything tighter trips on the usual
# 1e-15 datetime arithmetic noise.
_GRID_EPSILON_SECONDS: float = 1e-9

# Minimum number of samples drawn on the fine grid used by the TCA
# refinement step. Three is the smallest count that lets the bracketed
# minimiser identify a parabolic minimum.
_MIN_FINE_SAMPLES: int = 3

# Default sub-second tolerance handed to the bracketed minimiser. One
# millisecond is well below any operational requirement and is reached
# in a handful of objective evaluations.
_TCA_TOLERANCE_SECONDS: float = 1e-3


@dataclass(frozen=True)
class ScreeningParameters:
    """Configuration knobs for :func:`screen_population`.

    Centralising the parameters in a value object keeps the public API
    small and makes it easy to thread the screening configuration through
    the scheduler or use case calls.
    """

    coarse_step_seconds: float = 60.0
    fine_step_seconds: float = 1.0
    perigee_apogee_buffer_km: float = 50.0
    distance_threshold_km: float = 50.0
    probability_sigma_km: float = 1.0
    max_pairs: int | None = None


def perigee_apogee_compatible(
    propagator: Propagator,
    a: SatelliteState,
    b: SatelliteState,
    buffer_km: float = 50.0,
) -> bool:
    """Return ``True`` iff the satellites' altitude bands overlap within ``buffer_km``.

    This is the cheapest filter: it rejects pairs whose orbital shells
    cannot physically meet because their ``[perigee, apogee]`` intervals
    are disjoint by more than ``buffer_km``.
    """
    elements_a = propagator.orbital_elements(a.satrec)
    elements_b = propagator.orbital_elements(b.satrec)
    overlap_low = max(elements_a.perigee_altitude_km, elements_b.perigee_altitude_km)
    overlap_high = min(elements_a.apogee_altitude_km, elements_b.apogee_altitude_km)
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
        if i * step_seconds <= total + _GRID_EPSILON_SECONDS
    ]


def coarse_sweep(
    eph_a: Ephemeris,
    eph_b: Ephemeris,
    threshold_km: float,
) -> list[CandidateInterval]:
    """Identify intervals where the two ephemerides are within ``threshold_km``.

    The two ephemerides must share an identical time grid.

    Returns:
        A list of :class:`CandidateInterval`. The list is empty when no
        sample falls below ``threshold_km``.
    """
    if eph_a.times != eph_b.times:
        raise ValueError("ephemerides must share the same time grid")
    if len(eph_a.times) == 0:
        return []

    distances = np.linalg.norm(eph_a.positions - eph_b.positions, axis=1)
    below = distances < threshold_km
    if not np.any(below):
        return []

    return _below_threshold_intervals(eph_a.times, distances, below)


def _below_threshold_intervals(
    times: tuple[datetime, ...],
    distances: np.ndarray,
    below: np.ndarray,
) -> list[CandidateInterval]:
    """Walk the boolean mask and emit one :class:`CandidateInterval` per run."""
    intervals: list[CandidateInterval] = []
    in_interval = False
    start_idx = 0
    last_index = len(times) - 1
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
                    end_index=min(end_idx, last_index),
                    start_time=times[max(start_idx - 1, 0)],
                    end_time=times[min(end_idx, last_index)],
                    min_distance_km=float(distances[start_idx:end_idx].min()),
                )
            )
    if in_interval:
        end_idx = last_index
        intervals.append(
            CandidateInterval(
                start_index=max(start_idx - 1, 0),
                end_index=end_idx,
                start_time=times[max(start_idx - 1, 0)],
                end_time=times[end_idx],
                min_distance_km=float(distances[start_idx : end_idx + 1].min()),
            )
        )
    return intervals


def _distance_at(
    propagator: Propagator,
    state_a: object,
    state_b: object,
    t_seconds: float,
    t0: datetime,
) -> float:
    """Distance (km) at ``t0 + t_seconds`` between two propagator states."""
    when = t0 + timedelta(seconds=t_seconds)
    eph_a = propagator.propagate(state_a, [when])
    eph_b = propagator.propagate(state_b, [when])
    return float(np.linalg.norm(eph_a.positions[0] - eph_b.positions[0]))


def refine_tca(
    propagator: Propagator,
    minimizer: BoundedScalarMinimizer,
    sat_a: SatelliteState,
    sat_b: SatelliteState,
    interval: CandidateInterval,
    fine_step_seconds: float = 1.0,
) -> tuple[datetime, float, float]:
    """Refine the time of closest approach inside ``interval``.

    Returns:
        A tuple ``(tca, miss_distance_km, relative_velocity_km_s)``. The
        TCA is timezone-aware UTC; the relative velocity is the magnitude
        of the difference of the velocity vectors at the TCA.
    """
    t0 = interval.start_time
    span = (interval.end_time - interval.start_time).total_seconds()
    n_fine = max(math.ceil(span / fine_step_seconds) + 1, _MIN_FINE_SAMPLES)
    fine_times = [t0 + timedelta(seconds=i * span / (n_fine - 1)) for i in range(n_fine)]
    eph_a = propagator.propagate(sat_a.satrec, fine_times)
    eph_b = propagator.propagate(sat_b.satrec, fine_times)
    distances = np.linalg.norm(eph_a.positions - eph_b.positions, axis=1)
    best_idx = int(np.argmin(distances))

    bracket_lo, bracket_hi = _refinement_bracket(fine_times, t0, best_idx, n_fine)

    if bracket_hi <= bracket_lo:
        # Degenerate window -- return the best discrete sample.
        tca_offset = (fine_times[best_idx] - t0).total_seconds()
    else:
        tca_offset = minimizer.minimize(
            lambda t_seconds: _distance_at(propagator, sat_a.satrec, sat_b.satrec, t_seconds, t0),
            bracket_lo,
            bracket_hi,
            _TCA_TOLERANCE_SECONDS,
        )

    tca = t0 + timedelta(seconds=tca_offset)
    if tca.tzinfo is None:
        tca = tca.replace(tzinfo=UTC)

    eph_a_final = propagator.propagate(sat_a.satrec, [tca])
    eph_b_final = propagator.propagate(sat_b.satrec, [tca])
    miss = float(np.linalg.norm(eph_a_final.positions[0] - eph_b_final.positions[0]))
    rel_vel = float(np.linalg.norm(eph_a_final.velocities[0] - eph_b_final.velocities[0]))
    return tca, miss, rel_vel


def _refinement_bracket(
    fine_times: Sequence[datetime],
    t0: datetime,
    best_idx: int,
    n_fine: int,
) -> tuple[float, float]:
    """Return the offset bracket ``(lo, hi)`` (seconds since ``t0``) for the minimiser."""
    lo = max(best_idx - 1, 0)
    hi = min(best_idx + 1, n_fine - 1)
    return (
        (fine_times[lo] - t0).total_seconds(),
        (fine_times[hi] - t0).total_seconds(),
    )


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
    propagator: Propagator,
    minimizer: BoundedScalarMinimizer,
    sat_a: SatelliteState,
    sat_b: SatelliteState,
    start: datetime,
    end: datetime,
    parameters: ScreeningParameters | None = None,
) -> list[ConjunctionEvent]:
    """Screen one pair of satellites and return refined events."""
    p = parameters or ScreeningParameters()
    if sat_a.norad_id == sat_b.norad_id:
        return []
    if not perigee_apogee_compatible(
        propagator, sat_a, sat_b, buffer_km=p.perigee_apogee_buffer_km
    ):
        return []

    grid = _build_time_grid(start, end, p.coarse_step_seconds)
    eph_a = propagator.propagate(sat_a.satrec, grid)
    eph_b = propagator.propagate(sat_b.satrec, grid)
    intervals = coarse_sweep(eph_a, eph_b, p.distance_threshold_km)
    events: list[ConjunctionEvent] = []
    for interval in intervals:
        tca, miss, rel_vel = refine_tca(
            propagator,
            minimizer,
            sat_a,
            sat_b,
            interval,
            fine_step_seconds=p.fine_step_seconds,
        )
        if miss > p.distance_threshold_km:
            continue
        events.append(
            ConjunctionEvent(
                id=_generate_id(),
                sat_a=sat_a,
                sat_b=sat_b,
                tca=tca,
                miss_distance_km=miss,
                relative_velocity_km_s=rel_vel,
                probability=screening_probability(miss, p.probability_sigma_km),
            )
        )
    return events


def screen_population(
    propagator: Propagator,
    minimizer: BoundedScalarMinimizer,
    satellites: Sequence[SatelliteState],
    start: datetime,
    end: datetime,
    parameters: ScreeningParameters | None = None,
) -> list[ConjunctionEvent]:
    """Run the full three-tier screen across every distinct pair.

    Args:
        propagator: Adapter implementing :class:`oc.application.ports.Propagator`.
        minimizer: Adapter implementing
            :class:`oc.application.ports.BoundedScalarMinimizer`.
        satellites: Population to screen.
        start: Lower bound of the time window (UTC).
        end: Upper bound of the time window (UTC).
        parameters: Screening tuning knobs. Defaults to :class:`ScreeningParameters`.

    Returns:
        A list of :class:`ConjunctionEvent` sorted by ``miss_distance_km``.
    """
    p = parameters or ScreeningParameters()
    events: list[ConjunctionEvent] = []
    examined = 0
    for i in range(len(satellites)):
        for j in range(i + 1, len(satellites)):
            if p.max_pairs is not None and examined >= p.max_pairs:
                logger.warning(
                    "max_pairs limit reached", extra={"limit": p.max_pairs, "kept": len(events)}
                )
                return sorted(events, key=lambda e: e.miss_distance_km)
            examined += 1
            try:
                pair_events = screen_pair(
                    propagator,
                    minimizer,
                    satellites[i],
                    satellites[j],
                    start,
                    end,
                    parameters=p,
                )
            except Exception as exc:
                logger.warning(
                    "pair screening failed",
                    extra={
                        "sat_a": satellites[i].norad_id,
                        "sat_b": satellites[j].norad_id,
                        "error": str(exc),
                    },
                )
                continue
            events.extend(pair_events)
    return sorted(events, key=lambda e: e.miss_distance_km)
