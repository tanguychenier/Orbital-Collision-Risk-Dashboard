"""Backwards-compatibility shim for the SGP4 propagator.

The propagator was moved to
:mod:`oc.infrastructure.propagation.sgp4_propagator`. This module
re-exports the public surface so legacy imports keep working.
"""

from __future__ import annotations

from sgp4.api import Satrec

from oc.domain.value_objects import Ephemeris
from oc.infrastructure.propagation import (
    PropagationError,
    propagate,
    propagate_single,
    satrec_from_tle,
)
from oc.infrastructure.propagation import (
    orbital_elements as _orbital_elements,
)


def orbital_elements(satrec: Satrec) -> tuple[float, float, float]:
    """Return ``(sma_km, perigee_km, apogee_km)`` for the given ``Satrec``.

    The infrastructure adapter returns a richer
    :class:`oc.domain.value_objects.OrbitalElements` value object; this
    shim flattens it to the historical 3-tuple so existing callers
    continue to work.
    """
    elements = _orbital_elements(satrec)
    return (
        elements.semi_major_axis_km,
        elements.perigee_altitude_km,
        elements.apogee_altitude_km,
    )


__all__ = [
    "Ephemeris",
    "PropagationError",
    "orbital_elements",
    "propagate",
    "propagate_single",
    "satrec_from_tle",
]
