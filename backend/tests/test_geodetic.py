"""Unit tests for the TEME / ECEF / geodetic frame conversions."""

from __future__ import annotations

import math
from datetime import UTC, datetime

import numpy as np
import pytest

from oc.infrastructure.propagation.geodetic import (
    ecef_to_geodetic,
    gmst_radians,
    teme_to_ecef,
)

# WGS-84 reference equatorial radius (km).
_A_KM = 6378.137


def test_gmst_at_j2000_matches_published_value() -> None:
    """At the J2000.0 epoch, GMST is 18h 41m 50.54841s (Vallado 4ed table 3-2)."""
    j2000 = datetime(2000, 1, 1, 12, 0, 0, tzinfo=UTC)
    expected_seconds = 18.0 * 3600.0 + 41.0 * 60.0 + 50.54841
    expected_rad = expected_seconds / 240.0 * math.pi / 180.0
    expected_rad = expected_rad % (2.0 * math.pi)
    assert gmst_radians(j2000) == pytest.approx(expected_rad, abs=1e-6)


def test_gmst_advances_one_sidereal_day_in_one_solar_day() -> None:
    """Sidereal day is ~3m 56s shorter than the solar day."""
    t0 = datetime(2025, 1, 1, 0, 0, 0, tzinfo=UTC)
    t1 = datetime(2025, 1, 2, 0, 0, 0, tzinfo=UTC)
    delta = (gmst_radians(t1) - gmst_radians(t0)) % (2.0 * math.pi)
    # 24h of solar time advances GMST by 360 degrees + ~360/365.25 = ~0.9856 deg.
    expected_extra_rad = math.radians(360.0 / 365.25)
    assert delta == pytest.approx(expected_extra_rad, rel=5e-3)


def test_teme_to_ecef_at_zero_gmst_is_identity_on_z_axis() -> None:
    """On the rotation axis the conversion must be identity at any epoch."""
    when = datetime(2025, 6, 15, 12, 0, 0, tzinfo=UTC)
    z_only = np.array([0.0, 0.0, 7000.0])
    result = teme_to_ecef(z_only, when)
    assert result[0] == pytest.approx(0.0, abs=1e-9)
    assert result[1] == pytest.approx(0.0, abs=1e-9)
    assert result[2] == pytest.approx(7000.0)


def test_teme_to_ecef_preserves_norm() -> None:
    """The Z-axis rotation is rigid; the vector norm must not change."""
    when = datetime(2025, 6, 15, 13, 27, 31, tzinfo=UTC)
    teme = np.array([4500.0, -3300.0, 1800.0])
    ecef = teme_to_ecef(teme, when)
    assert float(np.linalg.norm(ecef)) == pytest.approx(
        float(np.linalg.norm(teme)), rel=1e-12
    )


def test_ecef_to_geodetic_equator_at_zero_meridian() -> None:
    """Surface point on the equator at longitude 0 has lat=0, lon=0, alt=0."""
    surface = np.array([_A_KM, 0.0, 0.0])
    lat, lon, alt = ecef_to_geodetic(surface)
    assert lat == pytest.approx(0.0, abs=1e-9)
    assert lon == pytest.approx(0.0, abs=1e-9)
    assert alt == pytest.approx(0.0, abs=1e-6)


def test_ecef_to_geodetic_north_pole() -> None:
    """At the rotation axis above the surface, lat must be +90 deg."""
    polar = np.array([0.0, 0.0, _A_KM + 500.0])
    lat, _, alt = ecef_to_geodetic(polar)
    assert lat == pytest.approx(90.0, abs=1e-6)
    # The polar radius is shorter than _A_KM, so altitude > 500 km.
    assert alt == pytest.approx(521.85, abs=1.0)


def test_ecef_to_geodetic_meridian_quadrants() -> None:
    """Longitude must follow the standard atan2 convention."""
    cases = {
        90.0: np.array([0.0, _A_KM, 0.0]),
        180.0: np.array([-_A_KM, 0.0, 0.0]),
        -90.0: np.array([0.0, -_A_KM, 0.0]),
    }
    for expected_lon, vec in cases.items():
        _, lon, _ = ecef_to_geodetic(vec)
        if expected_lon == 180.0:
            assert abs(lon) == pytest.approx(180.0, abs=1e-9)
        else:
            assert lon == pytest.approx(expected_lon, abs=1e-9)


def test_round_trip_geo_satellite_altitude() -> None:
    """GEO satellite at 0 deg longitude, equatorial: 35786 km altitude."""
    geo_radius = _A_KM + 35786.0
    ecef = np.array([geo_radius, 0.0, 0.0])
    lat, lon, alt = ecef_to_geodetic(ecef)
    assert lat == pytest.approx(0.0, abs=1e-9)
    assert lon == pytest.approx(0.0, abs=1e-9)
    assert alt == pytest.approx(35786.0, abs=1e-3)


def test_round_trip_iss_typical_orbit() -> None:
    """A typical ISS position (lat 25 deg, lon -50 deg, alt 420 km) round-trips."""
    lat0, lon0, alt0 = 25.0, -50.0, 420.0
    sin_lat, cos_lat = math.sin(math.radians(lat0)), math.cos(math.radians(lat0))
    sin_lon, cos_lon = math.sin(math.radians(lon0)), math.cos(math.radians(lon0))
    n = _A_KM / math.sqrt(1.0 - 0.00669437999014132 * sin_lat * sin_lat)
    x = (n + alt0) * cos_lat * cos_lon
    y = (n + alt0) * cos_lat * sin_lon
    z = (n * (1.0 - 0.00669437999014132) + alt0) * sin_lat
    lat, lon, alt = ecef_to_geodetic(np.array([x, y, z]))
    assert lat == pytest.approx(lat0, abs=1e-6)
    assert lon == pytest.approx(lon0, abs=1e-6)
    assert alt == pytest.approx(alt0, abs=1e-3)
