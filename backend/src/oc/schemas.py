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
