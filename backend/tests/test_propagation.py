"""Propagation tests against a known reference state."""

from __future__ import annotations

from datetime import UTC, datetime

import numpy as np
import pytest

from oc.services.propagation import (
    Ephemeris,
    PropagationError,
    orbital_elements,
    propagate,
    propagate_single,
    satrec_from_tle,
)

# ISS TLE used in the official sgp4 documentation, with a published reference
# ECI/TEME state vector at the given target epoch.
ISS_TLE_LINE1 = "1 25544U 98067A   19343.69339541  .00001764  00000-0  38792-4 0  9991"
ISS_TLE_LINE2 = "2 25544  51.6439 211.2001 0007417  17.6667  85.6398 15.50103472193511"
ISS_TARGET_EPOCH = datetime(2019, 12, 9, 12, 0, 0, tzinfo=UTC)
ISS_EXPECTED_R_KM = np.array([3520.60396351, -2626.76564681, 5174.40008759], dtype=np.float64)
ISS_EXPECTED_V_KM_S = np.array([5.72425888, 4.90230926, -1.39528633], dtype=np.float64)


def test_iss_position_within_one_kilometer() -> None:
    """Propagation of a known ISS TLE must reproduce the published position."""
    sat = satrec_from_tle(ISS_TLE_LINE1, ISS_TLE_LINE2)
    r, v = propagate_single(sat, ISS_TARGET_EPOCH)
    assert np.linalg.norm(r - ISS_EXPECTED_R_KM) < 1.0  # < 1 km
    assert np.linalg.norm(v - ISS_EXPECTED_V_KM_S) < 0.01  # < 10 m/s


def test_propagate_array_shapes_and_naive_datetime_handled() -> None:
    """Both naive and aware datetimes must produce the same trajectory."""
    sat = satrec_from_tle(ISS_TLE_LINE1, ISS_TLE_LINE2)
    naive = ISS_TARGET_EPOCH.replace(tzinfo=None)
    eph = propagate(sat, [naive, ISS_TARGET_EPOCH])
    assert isinstance(eph, Ephemeris)
    assert eph.positions.shape == (2, 3)
    assert eph.velocities.shape == (2, 3)
    assert eph.times[0].tzinfo is UTC
    np.testing.assert_allclose(eph.positions[0], eph.positions[1], atol=1e-6)


def test_orbital_elements_for_iss() -> None:
    """The semi-major axis must match the standard ISS altitude band."""
    sat = satrec_from_tle(ISS_TLE_LINE1, ISS_TLE_LINE2)
    sma_km, perigee_km, apogee_km = orbital_elements(sat)
    # ISS sits roughly at 400-420 km altitude; semi-major axis ~6790 km.
    assert 6700.0 < sma_km < 6900.0
    assert 380.0 < perigee_km < 430.0
    assert 380.0 < apogee_km < 430.0
    assert apogee_km >= perigee_km


def test_propagate_empty_input() -> None:
    """Propagating zero epochs returns an empty ephemeris."""
    sat = satrec_from_tle(ISS_TLE_LINE1, ISS_TLE_LINE2)
    eph = propagate(sat, [])
    assert eph.positions.shape == (0, 3)
    assert eph.velocities.shape == (0, 3)
    assert eph.times == ()


def test_propagate_invalid_epoch_raises() -> None:
    """A request for a date far in the future where SGP4 fails must raise."""
    sat = satrec_from_tle(ISS_TLE_LINE1, ISS_TLE_LINE2)
    very_far_future = datetime(3000, 1, 1, tzinfo=UTC)
    with pytest.raises(PropagationError):
        propagate(sat, [very_far_future])
