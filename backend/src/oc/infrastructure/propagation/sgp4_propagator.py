"""SGP4 propagator adapter.

Wraps the ``sgp4`` library so the rest of the codebase can talk to it
through the :class:`oc.application.ports.Propagator` port. The
free-standing helpers (:func:`propagate`, :func:`propagate_single`,
:func:`orbital_elements`, :func:`satrec_from_tle`) are kept as thin
module-level aliases — they are convenient for use-cases that need
sub-second TCA refinement and they preserve the public surface used by
the existing tests.
"""

from __future__ import annotations

from collections.abc import Sequence
from datetime import UTC, datetime

import numpy as np
from sgp4.api import SGP4_ERRORS, Satrec, jday

from oc.domain.value_objects import Ephemeris, OrbitalElements

# Earth equatorial radius used in the WGS-72 model that ships with sgp4.
_EARTH_RADIUS_KM: float = 6378.135


class PropagationError(RuntimeError):
    """Raised when ``sgp4`` reports a propagation failure for any sample."""


def satrec_from_tle(line1: str, line2: str) -> Satrec:
    """Construct a :class:`Satrec` from a 2-line TLE."""
    return Satrec.twoline2rv(line1, line2)


def _to_utc(dt: datetime) -> datetime:
    """Return ``dt`` as a timezone-aware UTC datetime."""
    if dt.tzinfo is None:
        return dt.replace(tzinfo=UTC)
    return dt.astimezone(UTC)


def _datetimes_to_jd(times: Sequence[datetime]) -> tuple[np.ndarray, np.ndarray]:
    """Convert a sequence of UTC datetimes to ``(jd, fr)`` arrays for ``sgp4``."""
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

    Args:
        satrec: An sgp4 :class:`Satrec` produced by :func:`satrec_from_tle`.
        times: UTC sample times.

    Returns:
        An :class:`Ephemeris` containing the position and velocity vectors
        in the TEME frame, expressed in kilometers and kilometers per second.

    Raises:
        PropagationError: If ``sgp4`` reports an error for any sample.
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
    """Propagate to a single epoch and return the ``(position, velocity)`` pair.

    The vectors are length-3 numpy arrays in the TEME frame, expressed in
    kilometers and kilometers per second.
    """
    eph = propagate(satrec, [when])
    return eph.positions[0], eph.velocities[0]


def orbital_elements(satrec: Satrec) -> OrbitalElements:
    """Return semi-major axis and perigee/apogee altitudes for a ``Satrec``.

    The semi-major axis is derived from ``a`` (Earth radii) on the satellite
    record. Perigee and apogee use the standard ``a*(1+/-e)`` relation;
    the returned altitudes are above Earth's mean radius (``WGS-72``).
    """
    sma_km = float(satrec.a) * _EARTH_RADIUS_KM
    ecc = float(satrec.ecco)
    perigee_alt = sma_km * (1.0 - ecc) - _EARTH_RADIUS_KM
    apogee_alt = sma_km * (1.0 + ecc) - _EARTH_RADIUS_KM
    return OrbitalElements(
        semi_major_axis_km=sma_km,
        perigee_altitude_km=perigee_alt,
        apogee_altitude_km=apogee_alt,
    )


class SGP4Propagator:
    """:class:`oc.application.ports.Propagator` implementation backed by ``sgp4``."""

    def build_state(self, line1: str, line2: str) -> object:
        """Compile a TLE into an opaque :class:`Satrec`."""
        return satrec_from_tle(line1, line2)

    def propagate(self, state: object, times: Sequence[datetime]) -> Ephemeris:
        """Propagate the underlying :class:`Satrec` to ``times``."""
        return propagate(_as_satrec(state), times)

    def orbital_elements(self, state: object) -> OrbitalElements:
        """Return :class:`OrbitalElements` for the underlying :class:`Satrec`."""
        return orbital_elements(_as_satrec(state))


def _as_satrec(state: object) -> Satrec:
    """Narrow an opaque propagator state to :class:`Satrec`."""
    if not isinstance(state, Satrec):
        raise TypeError(f"expected Satrec, got {type(state).__name__}")
    return state
