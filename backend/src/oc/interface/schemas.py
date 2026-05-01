"""Pydantic v2 schemas exposing the public API contract."""

from __future__ import annotations

from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field


class HealthResponse(BaseModel):
    """Payload for ``GET /api/health``."""

    status: str
    version: str
    tle_age_hours: float | None = Field(
        default=None,
        description="Age in hours of the most recent TLE epoch in the database.",
    )


class StatsResponse(BaseModel):
    """Payload for ``GET /api/stats``."""

    total_satellites: int
    total_active: int
    tle_last_updated: datetime | None
    conjunctions_24h: int
    conjunctions_72h: int
    high_risk_24h: int


class SatelliteSummary(BaseModel):
    """Short satellite reference embedded in conjunction lists."""

    model_config = ConfigDict(from_attributes=True)

    norad_id: int
    name: str


class SatelliteDetail(BaseModel):
    """Full satellite payload returned by ``GET /api/satellites``."""

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    norad_id: int
    name: str
    country: str | None = None
    object_type: str | None = Field(
        default=None,
        validation_alias="object_type",
        serialization_alias="type",
    )
    launch_date: date | None = None


class SatelliteConjunctionStats(BaseModel):
    """Counts of upcoming conjunctions over rolling windows for one satellite."""

    next_24h: int
    next_72h: int
    next_7d: int


class SatelliteDetailResponse(BaseModel):
    """Payload for ``GET /api/satellites/{id}``."""

    model_config = ConfigDict(populate_by_name=True)

    satellite: SatelliteDetail
    last_tle_epoch: datetime | None = None
    stats: SatelliteConjunctionStats


class GeodeticTCAPosition(BaseModel):
    """Sub-satellite point and altitude of one object at the conjunction's TCA.

    The point is in WGS-84 geodetic coordinates: ``latitude`` is the
    geodetic latitude in ``[-90, 90]``, ``longitude`` is in ``[-180, 180]``,
    and ``altitude_km`` is height above the WGS-84 ellipsoid (km).
    """

    latitude_deg: float = Field(ge=-90.0, le=90.0)
    longitude_deg: float = Field(ge=-180.0, le=180.0)
    altitude_km: float


class ConjunctionListItem(BaseModel):
    """One row in the ``GET /api/conjunctions`` list."""

    id: str
    sat_a: SatelliteSummary
    sat_b: SatelliteSummary
    tca: datetime
    miss_distance_km: float
    relative_velocity_km_s: float
    probability: float
    computed_at: datetime
    tca_position_a: GeodeticTCAPosition | None = Field(
        default=None,
        description=(
            "Sub-satellite point and altitude of satellite A at TCA. "
            "Null if propagation failed (corrupt TLE)."
        ),
    )
    tca_position_b: GeodeticTCAPosition | None = Field(
        default=None,
        description="Sub-satellite point and altitude of satellite B at TCA.",
    )


class ConjunctionDetail(BaseModel):
    """Full conjunction payload returned by ``GET /api/conjunctions/{id}``."""

    id: str
    sat_a: SatelliteDetail
    sat_b: SatelliteDetail
    tca: datetime
    miss_distance_km: float
    relative_velocity_km_s: float
    probability: float
    computed_at: datetime
    tle_a_line1: str
    tle_a_line2: str
    tle_b_line1: str
    tle_b_line2: str


class HeatmapAltitudeInclinationResponse(BaseModel):
    """Payload for ``GET /api/heatmap/altitude-inclination``.

    The matrix is row-major: ``counts[i][j]`` is the number of satellites
    whose orbit falls in altitude bin ``altitude_bands[i]`` and
    inclination bin ``inclination_bands[j]``. Both ``altitude_bands`` and
    ``inclination_bands`` carry the *lower edge* of each bin so the
    front-end can label its axes deterministically.
    """

    altitude_bands: list[float] = Field(
        description="Lower edge (km) of each altitude bin, ascending.",
    )
    inclination_bands: list[float] = Field(
        description="Lower edge (deg) of each inclination bin, ascending.",
    )
    altitude_step_km: float = Field(
        description="Width (km) of every altitude bin (constant).",
    )
    inclination_step_deg: float = Field(
        description="Width (deg) of every inclination bin (constant).",
    )
    counts: list[list[int]] = Field(
        description="Row-major matrix of satellite counts.",
    )
    total_satellites: int = Field(
        description="Total satellites whose orbit fell in the binning window.",
    )


class ConjunctionTimelinePoint(BaseModel):
    """One day in the ``GET /api/heatmap/conjunctions-timeline`` response."""

    date: date
    miss_lt_1km: int
    miss_lt_5km: int
    total: int


# --- Alert subsystem schemas -------------------------------------------------


class AlertSubscriptionCreate(BaseModel):
    """Payload accepted by ``POST /api/alerts/subscriptions``."""

    email_or_webhook_url: str = Field(
        description="Either a https:// webhook URL or a valid email address.",
        min_length=3,
        max_length=512,
    )
    norad_ids: list[int] = Field(
        description="NORAD catalog ids of satellites to watch.",
        min_length=1,
        max_length=50,
    )
    miss_distance_km_threshold: float = Field(
        default=5.0,
        ge=0.1,
        le=50.0,
        description="Conjunctions at or below this miss distance trigger an alert.",
    )


class AlertSubscriptionPublic(BaseModel):
    """Subscription view returned by GET / DELETE manage endpoints."""

    id: str
    email_or_webhook_url: str
    norad_ids: list[int]
    miss_distance_km_threshold: float
    is_active: bool
    created_at: datetime
    last_notified_at: datetime | None = None


class AlertSubscriptionCreated(BaseModel):
    """Payload returned by ``POST /api/alerts/subscriptions``."""

    id: str
    manage_url: str
