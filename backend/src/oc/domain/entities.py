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


# --- Heatmap binning constants (LEO-focused) ---------------------------------
# Altitude binning covers the operationally relevant LEO band where the bulk
# of the public catalogue lives. Anything outside ``[200 km, 2000 km]`` is
# excluded from the matrix so the rendered shape stays bounded.
HEATMAP_ALTITUDE_MIN_KM: float = 200.0
HEATMAP_ALTITUDE_MAX_KM: float = 2000.0
HEATMAP_ALTITUDE_STEP_KM: float = 50.0

# Inclination binning is exhaustive (0 to 180 degrees, including
# retrograde orbits which are common in sun-synchronous shells).
HEATMAP_INCLINATION_MIN_DEG: float = 0.0
HEATMAP_INCLINATION_MAX_DEG: float = 180.0
HEATMAP_INCLINATION_STEP_DEG: float = 5.0


@dataclass(frozen=True)
class OrbitalBin:
    """One satellite's coordinates in the heatmap binning grid.

    Attributes:
        altitude_km: Mean altitude (km) above Earth's mean radius. The
            binning rejects entries outside ``[HEATMAP_ALTITUDE_MIN_KM,
            HEATMAP_ALTITUDE_MAX_KM]``.
        inclination_deg: Orbital inclination (degrees) in ``[0, 180]``.
    """

    altitude_km: float
    inclination_deg: float


@dataclass(frozen=True)
class HeatmapMatrix:
    """A 2D matrix of satellite counts per altitude band x inclination band.

    Attributes:
        altitude_bands: Lower edge (km) of each altitude bin.
        inclination_bands: Lower edge (deg) of each inclination bin.
        counts: Row-major matrix where ``counts[i][j]`` is the number of
            satellites whose orbit falls in
            ``altitude_bands[i]`` x ``inclination_bands[j]``.
        total_satellites: Number of satellites that actually fell into a
            bin (i.e. excluding entries outside the LEO window).
    """

    altitude_bands: tuple[float, ...]
    inclination_bands: tuple[float, ...]
    counts: tuple[tuple[int, ...], ...]
    total_satellites: int


@dataclass(frozen=True)
class ConjunctionTimelinePoint:
    """One day's aggregated conjunction counts for the timeline endpoint.

    Attributes:
        date: Calendar day (UTC) the counts apply to.
        miss_lt_1km: Conjunctions with a miss distance below 1 km.
        miss_lt_5km: Conjunctions with a miss distance below 5 km.
        total: Total conjunctions whose ``tca`` falls on this day.
    """

    date: date
    miss_lt_1km: int
    miss_lt_5km: int
    total: int


@dataclass(frozen=True)
class AlertSubscription:
    """A CubeSat operator's standing request to be notified about conjunctions.

    The subsystem is intentionally stateless: there are no user accounts.
    The ``secret_token`` is the only credential and is meant to be
    embedded in the ``manage_url`` returned at creation time. Losing the
    token means losing the ability to inspect or unsubscribe.

    Attributes:
        id: Subscription primary key (UUID hex string).
        email_or_webhook_url: Either a webhook URL (``https://...``) or
            an email address.
        norad_ids: Tuple of NORAD catalog ids the operator wants alerts for.
        miss_distance_km_threshold: Conjunctions with a miss distance at
            or below this value trigger a notification.
        created_at: Timestamp the subscription was first persisted.
        last_notified_at: Timestamp of the most recent successful
            notification, or ``None`` if never notified.
        is_active: ``False`` once the operator has unsubscribed.
        secret_token: Token authenticating the manage URL.
    """

    id: str
    email_or_webhook_url: str
    norad_ids: tuple[int, ...]
    miss_distance_km_threshold: float
    created_at: datetime
    secret_token: str
    last_notified_at: datetime | None = None
    is_active: bool = True
