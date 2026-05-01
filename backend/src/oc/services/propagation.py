"""Thin wrapper around the ``sgp4`` library for orbit propagation.

The wrapper accepts a ``Satrec`` (or its ``(line1, line2)`` definition) and a
sequence of UTC datetimes and returns position/velocity vectors in the TEME
frame (kilometers, kilometers per second).
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import UTC, datetime

import numpy as np
from sgp4.api import SGP4_ERRORS, Satrec, jday


class PropagationError(RuntimeError):
    """Raised when ``sgp4`` reports a propagation failure for any sample."""


@dataclass(frozen=True)
class Ephemeris:
    """A propagated trajectory.

    Attributes:
        times: UTC sample times (length ``N``).
        positions: ``(N, 3)`` array of position vectors (km, TEME).
        velocities: ``(N, 3)`` array of velocity vectors (km/s, TEME).
    """

    times: tuple[datetime, ...]
    positions: np.ndarray
    velocities: np.ndarray

    def __post_init__(self) -> None:
        if self.positions.shape != (len(self.times), 3):
            raise ValueError("positions shape mismatch")
        if self.velocities.shape != (len(self.times), 3):
            raise ValueError("velocities shape mismatch")


def satrec_from_tle(line1: str, line2: str) -> Satrec:
    """Construct a :class:`Satrec` from a 2-line TLE."""
    return Satrec.twoline2rv(line1, line2)


def _to_utc(dt: datetime) -> datetime:
    """Return ``dt`` as a timezone-aware UTC datetime."""
    if dt.tzinfo is None:
        return dt.replace(tzinfo=UTC)
    return dt.astimezone(UTC)


def _datetimes_to_jd(times: Sequence[datetime]) -> tuple[np.ndarray, np.ndarray]:
    """Convert a sequence of UTC datetimes to (jd, fr) arrays for ``sgp4``."""
    jds = np.empty(len(times), dtype=np.float64)
    frs = np.empty(len(times), dtype=np.float64)
    for i, t in enumerate(times):
        u = _to_utc(t)
        jd, fr = jday(
            u.year,
            u.month,
            u.day,
            u.hour,
            u.minute,
            u.second + u.microsecond * 1e-6,
        )
        jds[i] = jd
        frs[i] = fr
    return jds, frs


def propagate(satrec: Satrec, times: Sequence[datetime]) -> Ephemeris:
    """Propagate ``satrec`` to each datetime in ``times``.

    Returns an :class:`Ephemeris` containing the position and velocity vectors
    in the TEME frame in kilometers and kilometers per second.

    Raises:
        PropagationError: if ``sgp4`` reports an error for any sample.
    """
    if not times:
        empty = np.zeros((0, 3), dtype=np.float64)
        return Ephemeris(times=(), positions=empty, velocities=empty)

    jd, fr = _datetimes_to_jd(times)
    err, r, v = satrec.sgp4_array(jd, fr)
    if np.any(err):
        nonzero = int(np.argmax(err != 0))
        code = int(err[nonzero])
        msg = SGP4_ERRORS.get(code, f"unknown sgp4 error {code}")
        raise PropagationError(f"sgp4 error at index {nonzero}: {msg}")
    return Ephemeris(
        times=tuple(_to_utc(t) for t in times),
        positions=np.asarray(r, dtype=np.float64),
        velocities=np.asarray(v, dtype=np.float64),
    )


def propagate_single(satrec: Satrec, when: datetime) -> tuple[np.ndarray, np.ndarray]:
    """Convenience wrapper to propagate to a single epoch.

    Returns:
        A pair ``(r, v)`` where ``r`` and ``v`` are length-3 numpy arrays
        (kilometers and kilometers per second, TEME frame).
    """
    eph = propagate(satrec, [when])
    return eph.positions[0], eph.velocities[0]


def orbital_elements(satrec: Satrec) -> tuple[float, float, float]:
    """Return ``(sma_km, perigee_km, apogee_km)`` from a ``Satrec``.

    The semi-major axis is derived from ``a`` (Earth radii) on the satellite
    record, and perigee/apogee use the standard ``a*(1+/-e)`` relation. The
    returned perigee/apogee are altitudes above Earth's mean radius.
    """
    earth_radius_km = 6378.135
    sma_km = float(satrec.a) * earth_radius_km
    ecc = float(satrec.ecco)
    perigee_alt = sma_km * (1.0 - ecc) - earth_radius_km
    apogee_alt = sma_km * (1.0 + ecc) - earth_radius_km
    return sma_km, perigee_alt, apogee_alt
