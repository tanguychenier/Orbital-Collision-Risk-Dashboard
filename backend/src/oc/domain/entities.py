"""Domain entities.

Entities are framework-agnostic dataclasses. They never import SQLAlchemy,
Pydantic, FastAPI, sgp4, or any other driver. The application layer
operates on these types; adapters in ``infrastructure`` translate them
to/from external representations (ORM rows, HTTP payloads, ...).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime


@dataclass(frozen=True)
class SatelliteRecord:
    """A tracked space object identified by its NORAD catalog id."""

    norad_id: int
    name: str
    country: str | None = None
    object_type: str | None = None
    launch_date: date | None = None
    is_active: bool = True


@dataclass(frozen=True)
class TLERecord:
    """A Two-Line Element record bound to a satellite."""

    norad_id: int
    epoch: datetime
    line1: str
    line2: str
    db_id: int | None = None


@dataclass(frozen=True)
class ParsedTLE:
    """A 3-line TLE parsed from a CelesTrak text feed.

    Attributes:
        name: Satellite name (line 0 of the 3-line block).
        norad_id: NORAD catalog id from columns 3-7 of line 1.
        line1: Raw TLE line 1.
        line2: Raw TLE line 2.
        epoch: Decoded epoch as a UTC ``datetime``.
    """

    name: str
    norad_id: int
    line1: str
    line2: str
    epoch: datetime


@dataclass(frozen=True)
class ConjunctionEvent:
    """A predicted close approach between two satellites.

    The associated ``SatelliteState`` instances carry the propagator state
    (``Satrec``) needed by the screening pipeline. Only the public scalar
    attributes (``id``, ``tca``, ``miss_distance_km`` ...) are part of the
    persistence contract; ``sat_a`` / ``sat_b`` are runtime-only references.
    """

    id: str
    sat_a: SatelliteState
    sat_b: SatelliteState
    tca: datetime
    miss_distance_km: float
    relative_velocity_km_s: float
    probability: float


@dataclass(frozen=True)
class SatelliteState:
    """Container linking a satellite's identifiers and its propagator handle.

    The ``satrec`` field is intentionally typed as ``object`` in this
    domain layer to avoid pulling sgp4 into the domain. The screening
    use case treats it as opaque and passes it back to a ``Propagator``
    port.
    """

    norad_id: int
    name: str
    line1: str
    line2: str
    satrec: object = field(repr=False)
    tle_db_id: int | None = None
