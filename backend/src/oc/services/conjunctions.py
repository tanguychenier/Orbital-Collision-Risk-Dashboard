"""Backwards-compatibility shim for the conjunction screening pipeline.

The hexagonal refactor moved the screening algorithm to
:mod:`oc.application.use_cases.compute_conjunctions`. This module wraps
the use case with default SGP4/scipy adapters so existing call sites
continue to work without an explicit dependency injection step.
"""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from dataclasses import replace
from datetime import datetime
from typing import Any

from oc.application.use_cases import compute_conjunctions as _use_case
from oc.application.use_cases.compute_conjunctions import ScreeningParameters
from oc.domain.entities import ConjunctionEvent
from oc.domain.entities import SatelliteState as _DomainSatelliteState
from oc.domain.value_objects import CandidateInterval
from oc.infrastructure.numerics import ScipyBoundedMinimizer
from oc.infrastructure.propagation import SGP4Propagator, satrec_from_tle

# Default singletons. The screening pipeline is stateless so it is safe
# to share a single propagator/minimizer across the process.
_PROPAGATOR = SGP4Propagator()
_MINIMIZER = ScipyBoundedMinimizer()


class SatelliteState(_DomainSatelliteState):
    """Domain :class:`SatelliteState` extended with a ``from_tle`` factory."""

    @classmethod
    def from_tle(
        cls,
        norad_id: int,
        name: str,
        line1: str,
        line2: str,
        tle_db_id: int | None = None,
    ) -> SatelliteState:
        """Build a :class:`SatelliteState` and pre-construct its ``Satrec``."""
        return cls(
            norad_id=norad_id,
            name=name,
            line1=line1,
            line2=line2,
            tle_db_id=tle_db_id,
            satrec=satrec_from_tle(line1, line2),
        )


def perigee_apogee_compatible(
    a: _DomainSatelliteState,
    b: _DomainSatelliteState,
    buffer_km: float = 50.0,
) -> bool:
    """Backwards-compatible alias of the use-case ``perigee_apogee_compatible``."""
    return _use_case.perigee_apogee_compatible(_PROPAGATOR, a, b, buffer_km=buffer_km)


def coarse_sweep(eph_a: Any, eph_b: Any, threshold_km: float) -> list[CandidateInterval]:
    """Backwards-compatible alias of the use-case ``coarse_sweep``."""
    return _use_case.coarse_sweep(eph_a, eph_b, threshold_km)


def refine_tca(
    sat_a: _DomainSatelliteState,
    sat_b: _DomainSatelliteState,
    interval: CandidateInterval,
    fine_step_seconds: float = 1.0,
) -> tuple[datetime, float, float]:
    """Backwards-compatible alias of the use-case ``refine_tca``."""
    return _use_case.refine_tca(
        _PROPAGATOR, _MINIMIZER, sat_a, sat_b, interval, fine_step_seconds=fine_step_seconds
    )


def screening_probability(miss_km: float, sigma_km: float = 1.0) -> float:
    """Backwards-compatible alias of the use-case ``screening_probability``."""
    return _use_case.screening_probability(miss_km, sigma_km=sigma_km)


def screen_pair(
    sat_a: _DomainSatelliteState,
    sat_b: _DomainSatelliteState,
    start: datetime,
    end: datetime,
    coarse_step_seconds: float = 60.0,
    fine_step_seconds: float = 1.0,
    perigee_apogee_buffer_km: float = 50.0,
    distance_threshold_km: float = 50.0,
    probability_sigma_km: float = 1.0,
) -> list[ConjunctionEvent]:
    """Backwards-compatible alias of the use-case ``screen_pair``."""
    parameters = ScreeningParameters(
        coarse_step_seconds=coarse_step_seconds,
        fine_step_seconds=fine_step_seconds,
        perigee_apogee_buffer_km=perigee_apogee_buffer_km,
        distance_threshold_km=distance_threshold_km,
        probability_sigma_km=probability_sigma_km,
    )
    return _use_case.screen_pair(_PROPAGATOR, _MINIMIZER, sat_a, sat_b, start, end, parameters)


def screen_population(
    satellites: Sequence[_DomainSatelliteState],
    start: datetime,
    end: datetime,
    coarse_step_seconds: float = 60.0,
    fine_step_seconds: float = 1.0,
    perigee_apogee_buffer_km: float = 50.0,
    distance_threshold_km: float = 50.0,
    probability_sigma_km: float = 1.0,
    max_pairs: int | None = None,
) -> list[ConjunctionEvent]:
    """Backwards-compatible alias of the use-case ``screen_population``."""
    parameters = ScreeningParameters(
        coarse_step_seconds=coarse_step_seconds,
        fine_step_seconds=fine_step_seconds,
        perigee_apogee_buffer_km=perigee_apogee_buffer_km,
        distance_threshold_km=distance_threshold_km,
        probability_sigma_km=probability_sigma_km,
        max_pairs=max_pairs,
    )
    return _use_case.screen_population(_PROPAGATOR, _MINIMIZER, satellites, start, end, parameters)


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


# ``replace`` is re-exported only because some downstream code may rely on it.
__all__ = [
    "CandidateInterval",
    "ConjunctionEvent",
    "SatelliteState",
    "ScreeningParameters",
    "coarse_sweep",
    "perigee_apogee_compatible",
    "refine_tca",
    "replace",
    "screen_pair",
    "screen_population",
    "screening_probability",
    "states_from_records",
]
