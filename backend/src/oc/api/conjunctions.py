"""``/api/conjunctions`` endpoints."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from oc.config import Settings, get_settings
from oc.db import get_db_session
from oc.models import Conjunction
from oc.schemas import (
    ConjunctionDetail,
    ConjunctionListItem,
    SatelliteDetail,
    SatelliteSummary,
)

router = APIRouter()


def _ensure_utc(dt: datetime) -> datetime:
    return dt if dt.tzinfo is not None else dt.replace(tzinfo=UTC)


@router.get("/conjunctions", response_model=list[ConjunctionListItem])
async def list_conjunctions(
    max_distance_km: float = Query(default=5.0, gt=0.0, le=1000.0),
    hours: float = Query(default=72.0, gt=0.0, le=24.0 * 30.0),
    limit: int = Query(default=200, ge=1, le=1000),
    offset: int = Query(default=0, ge=0),
    session: AsyncSession = Depends(get_db_session),
    settings: Settings = Depends(get_settings),
) -> list[ConjunctionListItem]:
    """Return upcoming conjunctions filtered by miss distance and horizon."""
    now = datetime.now(UTC)
    horizon = now + timedelta(hours=hours)
    capped_limit = min(limit, settings.api_max_limit)
    stmt = (
        select(Conjunction)
        .options(selectinload(Conjunction.sat_a), selectinload(Conjunction.sat_b))
        .where(
            Conjunction.tca >= now,
            Conjunction.tca <= horizon,
            Conjunction.miss_distance_km <= max_distance_km,
        )
        .order_by(Conjunction.tca)
        .offset(offset)
        .limit(capped_limit)
    )
    result = await session.execute(stmt)
    conjunctions = result.scalars().all()
    return [
        ConjunctionListItem(
            id=c.id,
            sat_a=SatelliteSummary(norad_id=c.sat_a.norad_id, name=c.sat_a.name),
            sat_b=SatelliteSummary(norad_id=c.sat_b.norad_id, name=c.sat_b.name),
            tca=_ensure_utc(c.tca),
            miss_distance_km=c.miss_distance_km,
            relative_velocity_km_s=c.relative_velocity_km_s,
            probability=c.probability,
            computed_at=_ensure_utc(c.computed_at),
        )
        for c in conjunctions
    ]


@router.get(
    "/conjunctions/{conjunction_id}",
    response_model=ConjunctionDetail,
    response_model_by_alias=True,
)
async def get_conjunction(
    conjunction_id: str,
    session: AsyncSession = Depends(get_db_session),
) -> ConjunctionDetail:
    """Return one conjunction with the originating TLEs included."""
    stmt = (
        select(Conjunction)
        .options(
            selectinload(Conjunction.sat_a),
            selectinload(Conjunction.sat_b),
            selectinload(Conjunction.tle_a),
            selectinload(Conjunction.tle_b),
        )
        .where(Conjunction.id == conjunction_id)
    )
    result = await session.execute(stmt)
    c = result.scalar_one_or_none()
    if c is None:
        raise HTTPException(status_code=404, detail="conjunction not found")
    return ConjunctionDetail(
        id=c.id,
        sat_a=SatelliteDetail.model_validate(c.sat_a, from_attributes=True),
        sat_b=SatelliteDetail.model_validate(c.sat_b, from_attributes=True),
        tca=_ensure_utc(c.tca),
        miss_distance_km=c.miss_distance_km,
        relative_velocity_km_s=c.relative_velocity_km_s,
        probability=c.probability,
        computed_at=_ensure_utc(c.computed_at),
        tle_a_line1=c.tle_a.line1,
        tle_a_line2=c.tle_a.line2,
        tle_b_line1=c.tle_b.line1,
        tle_b_line2=c.tle_b.line2,
    )
