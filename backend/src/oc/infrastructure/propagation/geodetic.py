"""TEME / ECEF / geodetic frame conversions.

The screening pipeline propagates Two-Line Elements through ``sgp4``,
which delivers state vectors in the TEME (True Equator Mean Equinox)
frame. To plot a satellite at the right longitude on a Cesium globe we
need geodetic coordinates: latitude, longitude, and altitude above the
WGS-84 ellipsoid.

Two transformations are involved:

1. ``TEME -> ECEF`` -- rotate around the Z axis by the Greenwich Mean
   Sidereal Time (GMST). Polar motion is intentionally skipped: it is
   below 30 metres which is well under the level-2 imagery resolution
   used by the dashboard.
2. ``ECEF -> geodetic`` -- closed-form Bowring iteration on the WGS-84
   ellipsoid. One Newton step is enough for sub-metre accuracy at any
   altitude relevant to the screening catalogue.

The functions are framework-free numpy wrappers; they belong to the
``infrastructure.propagation`` layer because they manipulate the same
state vectors as :mod:`sgp4_propagator`.
"""

from __future__ import annotations

import math
from datetime import UTC, datetime

import numpy as np
from sgp4.api import jday

# WGS-84 reference ellipsoid (canonical defining parameters).
_WGS84_A_KM: float = 6378.137
_WGS84_F: float = 1.0 / 298.257223563
_WGS84_E2: float = _WGS84_F * (2.0 - _WGS84_F)
_WGS84_B_KM: float = _WGS84_A_KM * (1.0 - _WGS84_F)


def _to_utc(dt: datetime) -> datetime:
    """Return ``dt`` as a timezone-aware UTC datetime."""
    if dt.tzinfo is None:
        return dt.replace(tzinfo=UTC)
    return dt.astimezone(UTC)


def gmst_radians(when: datetime) -> float:
    """Return the Greenwich Mean Sidereal Time at ``when`` in radians.

    Uses the IAU 1982 polynomial (good to a few milli-arcseconds over
    decades, which is far better than required for satellite plotting).
    """
    u = _to_utc(when)
    jd_int, jd_frac = jday(
        u.year,
        u.month,
        u.day,
        u.hour,
        u.minute,
        u.second + u.microsecond * 1e-6,
    )
    jd = jd_int + jd_frac
    t = (jd - 2451545.0) / 36525.0
    gmst_seconds = (
        67310.54841
        + (876600.0 * 3600.0 + 8640184.812866) * t
        + 0.093104 * t * t
        - 6.2e-6 * t * t * t
    )
    gmst_rad = (gmst_seconds % 86400.0) / 240.0 * math.pi / 180.0
    return float(gmst_rad % (2.0 * math.pi))


def teme_to_ecef(position_teme_km: np.ndarray, when: datetime) -> np.ndarray:
    """Rotate a TEME position vector into ECEF at the requested epoch.

    Polar motion is ignored (sub-30 m bias).

    Args:
        position_teme_km: shape ``(3,)`` array (km).
        when: UTC epoch the vector applies to.

    Returns:
        A new shape ``(3,)`` numpy array expressed in ECEF (km).
    """
    theta = gmst_radians(when)
    c = math.cos(theta)
    s = math.sin(theta)
    x, y, z = (
        float(position_teme_km[0]),
        float(position_teme_km[1]),
        float(position_teme_km[2]),
    )
    return np.array([c * x + s * y, -s * x + c * y, z], dtype=np.float64)


def ecef_to_geodetic(position_ecef_km: np.ndarray) -> tuple[float, float, float]:
    """Convert an ECEF position to ``(lat_deg, lon_deg, alt_km)``.

    Uses Bowring's closed-form approximation followed by one Newton
    iteration. Produces sub-metre accuracy from the surface to GEO.

    Args:
        position_ecef_km: shape ``(3,)`` numpy array (km).

    Returns:
        ``(latitude_deg, longitude_deg, altitude_km)`` with longitude in
        ``[-180, 180]`` and latitude in ``[-90, 90]``.
    """
    x, y, z = (
        float(position_ecef_km[0]),
        float(position_ecef_km[1]),
        float(position_ecef_km[2]),
    )
    r = math.hypot(x, y)
    if r == 0.0:
        # Degenerate: vector aligned with the rotation axis. Lat = +/- 90.
        sign = 1.0 if z >= 0.0 else -1.0
        return sign * 90.0, 0.0, abs(z) - _WGS84_B_KM

    # Bowring's reduced latitude.
    beta = math.atan2(z * _WGS84_A_KM, r * _WGS84_B_KM)
    sin_beta3 = math.sin(beta) ** 3
    cos_beta3 = math.cos(beta) ** 3
    lat = math.atan2(
        z + _WGS84_E2 * _WGS84_B_KM * sin_beta3 / (1.0 - _WGS84_E2),
        r - _WGS84_E2 * _WGS84_A_KM * cos_beta3,
    )
    sin_lat = math.sin(lat)
    n = _WGS84_A_KM / math.sqrt(1.0 - _WGS84_E2 * sin_lat * sin_lat)
    alt = r / math.cos(lat) - n
    lon = math.atan2(y, x)
    return math.degrees(lat), math.degrees(lon), alt
