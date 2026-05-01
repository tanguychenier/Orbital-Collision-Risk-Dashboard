"""End-to-end tests of the conjunction screening pipeline.

A pair of synthetic orbits is constructed via :meth:`Satrec.sgp4init` so that
the two satellites cross at a well-defined time-of-closest-approach (TCA) with
a known miss distance. The test then runs the screener and asserts that:

* the TCA is recovered within 1 second;
* the miss distance is recovered within 100 metres;
* the perigee/apogee filter rejects pairs whose altitude bands cannot meet.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import numpy as np
import pytest
from sgp4.api import WGS72, Satrec
from sgp4.exporter import export_tle

from oc.services.conjunctions import (
    SatelliteState,
    coarse_sweep,
    perigee_apogee_compatible,
    screen_pair,
    screen_population,
    screening_probability,
)
from oc.services.propagation import propagate

# Synthetic scenario constants.
EPOCH_DT = datetime(2020, 1, 1, 0, 0, 0, tzinfo=UTC)
T_OFFSET_SECONDS = 300.0  # closest approach 5 minutes past epoch
MEAN_MOTION_REV_PER_DAY = 15.0


def _epoch_days_since_1949(dt: datetime) -> float:
    base = datetime(1949, 12, 31, tzinfo=UTC)
    return (dt - base).total_seconds() / 86400.0


def _build_state(
    norad_id: int,
    name: str,
    inclination_deg: float,
    raan_deg: float,
    ma0_rad: float,
    mean_motion_rev_per_day: float = MEAN_MOTION_REV_PER_DAY,
) -> SatelliteState:
    """Build a SatelliteState by initialising sgp4 from elements + exporting TLEs."""
    epoch_d = _epoch_days_since_1949(EPOCH_DT)
    n_rad_per_min = mean_motion_rev_per_day * 2.0 * np.pi / 1440.0
    sat = Satrec()
    sat.sgp4init(
        WGS72,
        "i",
        norad_id,
        epoch_d,
        0.0,  # bstar
        0.0,  # ndot
        0.0,  # nddot
        0.0,  # ecco
        0.0,  # argpo
        np.radians(inclination_deg),
        ma0_rad,
        n_rad_per_min,
        np.radians(raan_deg),
    )
    line1, line2 = export_tle(sat)
    return SatelliteState.from_tle(norad_id=norad_id, name=name, line1=line1, line2=line2)


@pytest.fixture()
def crossing_pair() -> tuple[SatelliteState, SatelliteState]:
    """Two satellites that pass within ~20 m at ``EPOCH_DT + 300 s``."""
    n_a_rad_per_sec = MEAN_MOTION_REV_PER_DAY * 2.0 * np.pi / 86400.0
    # MA reaches 2*pi at TCA; we wrap into [0, 2*pi).
    ma_at_epoch = (-n_a_rad_per_sec * T_OFFSET_SECONDS) % (2.0 * np.pi)
    sat_a = _build_state(99001, "SYNTH-A", inclination_deg=51.0, raan_deg=0.0, ma0_rad=ma_at_epoch)
    sat_b = _build_state(99002, "SYNTH-B", inclination_deg=51.05, raan_deg=0.0, ma0_rad=ma_at_epoch)
    return sat_a, sat_b


def test_perigee_apogee_filter_rejects_disjoint_orbits() -> None:
    """Two satellites at very different altitudes must be rejected."""
    leo = _build_state(99100, "LEO", 50.0, 0.0, 0.0, mean_motion_rev_per_day=15.0)
    geo = _build_state(99200, "GEO", 0.05, 0.0, 0.0, mean_motion_rev_per_day=1.002)
    assert not perigee_apogee_compatible(leo, geo, buffer_km=50.0)


def test_perigee_apogee_filter_keeps_co_altitude_orbits(
    crossing_pair: tuple[SatelliteState, SatelliteState],
) -> None:
    """The synthetic crossing pair must pass the altitude filter."""
    sat_a, sat_b = crossing_pair
    assert perigee_apogee_compatible(sat_a, sat_b, buffer_km=50.0)


def test_coarse_sweep_finds_candidate_window(
    crossing_pair: tuple[SatelliteState, SatelliteState],
) -> None:
    """The 60 s sweep must produce one candidate interval covering the TCA."""
    sat_a, sat_b = crossing_pair
    grid = [EPOCH_DT + timedelta(seconds=60 * i) for i in range(11)]  # 0..600 s
    eph_a = propagate(sat_a.satrec, grid)
    eph_b = propagate(sat_b.satrec, grid)
    intervals = coarse_sweep(eph_a, eph_b, threshold_km=50.0)
    assert len(intervals) == 1
    interval = intervals[0]
    assert interval.start_time <= EPOCH_DT + timedelta(seconds=T_OFFSET_SECONDS)
    assert interval.end_time >= EPOCH_DT + timedelta(seconds=T_OFFSET_SECONDS)


def _ground_truth_tca(
    sat_a: SatelliteState, sat_b: SatelliteState, t0: datetime, t1: datetime
) -> tuple[datetime, float]:
    """Brute-force the true TCA at 0.05 s resolution. Used as the test oracle."""
    span = (t1 - t0).total_seconds()
    n = int(span / 0.05) + 1
    times = [t0 + timedelta(seconds=i * 0.05) for i in range(n)]
    eph_a = propagate(sat_a.satrec, times)
    eph_b = propagate(sat_b.satrec, times)
    distances = np.linalg.norm(eph_a.positions - eph_b.positions, axis=1)
    idx = int(np.argmin(distances))
    return times[idx], float(distances[idx])


def test_screen_pair_recovers_known_tca_and_miss(
    crossing_pair: tuple[SatelliteState, SatelliteState],
) -> None:
    """``screen_pair`` must match the brute-force TCA within 1 s and 100 m."""
    sat_a, sat_b = crossing_pair
    horizon = EPOCH_DT + timedelta(seconds=900)
    events = screen_pair(
        sat_a,
        sat_b,
        EPOCH_DT,
        horizon,
        coarse_step_seconds=60.0,
        fine_step_seconds=1.0,
        distance_threshold_km=50.0,
    )
    assert len(events) == 1
    event = events[0]

    # Reference TCA from a high-resolution brute-force search around the event.
    truth_t, truth_miss = _ground_truth_tca(
        sat_a,
        sat_b,
        EPOCH_DT + timedelta(seconds=T_OFFSET_SECONDS - 60.0),
        EPOCH_DT + timedelta(seconds=T_OFFSET_SECONDS + 60.0),
    )
    delta_t = abs((event.tca - truth_t).total_seconds())
    assert delta_t < 1.0, f"|delta_t| = {delta_t:.3f} s exceeds 1 s"
    assert abs(event.miss_distance_km - truth_miss) < 0.1, (
        f"miss difference {abs(event.miss_distance_km - truth_miss):.4f} km > 100 m"
    )
    assert event.miss_distance_km < 0.5  # synthetic crossing is well under 500 m
    assert event.relative_velocity_km_s > 0.0
    # Probability proxy should be a sensible value in (0, 1].
    assert 0.0 < event.probability <= 1.0


def test_screen_population_aggregates_pairs(
    crossing_pair: tuple[SatelliteState, SatelliteState],
) -> None:
    """``screen_population`` must return at least the synthetic event."""
    sat_a, sat_b = crossing_pair
    far = _build_state(99300, "FAR", 95.0, 180.0, 0.0, mean_motion_rev_per_day=14.0)
    horizon = EPOCH_DT + timedelta(seconds=900)
    events = screen_population(
        [sat_a, sat_b, far],
        EPOCH_DT,
        horizon,
        coarse_step_seconds=60.0,
        fine_step_seconds=1.0,
    )
    assert len(events) >= 1
    norad_pairs = {(e.sat_a.norad_id, e.sat_b.norad_id) for e in events}
    assert (99001, 99002) in norad_pairs or (99002, 99001) in norad_pairs


def test_screening_probability_decays() -> None:
    """The probability proxy must monotonically decay with miss distance."""
    p_close = screening_probability(0.1, sigma_km=1.0)
    p_far = screening_probability(5.0, sigma_km=1.0)
    assert p_close > p_far
    assert 0.0 < p_far < p_close <= 1.0


def test_screening_probability_validation() -> None:
    """A non-positive sigma must raise."""
    with pytest.raises(ValueError):
        screening_probability(1.0, sigma_km=0.0)
