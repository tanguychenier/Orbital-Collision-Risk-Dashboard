"""Pure domain layer.

Contains entities and value objects that describe the business problem
(satellites, TLEs, conjunctions) without any framework, database, or
third-party driver dependency.

Nothing in this package may import from ``infrastructure``,
``application``, or any external library beyond the Python standard
library and ``numpy`` (used as a value-object for vector math).
"""

from oc.domain.entities import (
    ConjunctionEvent,
    ParsedTLE,
    SatelliteRecord,
    TLERecord,
)
from oc.domain.value_objects import (
    CandidateInterval,
    Ephemeris,
    OrbitalElements,
    StateVector,
)

__all__ = [
    "CandidateInterval",
    "ConjunctionEvent",
    "Ephemeris",
    "OrbitalElements",
    "ParsedTLE",
    "SatelliteRecord",
    "StateVector",
    "TLERecord",
]
