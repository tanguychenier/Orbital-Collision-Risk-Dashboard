"""``/api/stats`` endpoint."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from oc.db import get_db_session
from oc.models import TLE, Conjunction, Satellite
from oc.schemas import StatsResponse

router = APIRouter()


@router.get("/stats", response_model=StatsResponse)
async def stats(session: AsyncSession = Depends(get_db_session)) -> StatsResponse:
    """Population, ingestion freshness, and conjunction counts."""
    now = datetime.now(UTC)
    horizon_24h = now + timedelta(hours=24)
    horizon_72h = now + timedelta(hours=72)

    total_satellites = await session.scalar(select(func.count()).select_from(Satellite)) or 0
    total_active = (
        await session.scalar(
            select(func.count()).select_from(Satellite).where(Satellite.is_active.is_(True))
        )
    ) or 0
    last_updated = await session.scalar(select(func.max(TLE.epoch)))
    if last_updated is not None and last_updated.tzinfo is None:
        last_updated = last_updated.replace(tzinfo=UTC)

    conj_24h = (
        await session.scalar(
            select(func.count())
            .select_from(Conjunction)
            .where(Conjunction.tca >= now, Conjunction.tca <= horizon_24h)
        )
    ) or 0
    conj_72h = (
        await session.scalar(
            select(func.count())
            .select_from(Conjunction)
            .where(Conjunction.tca >= now, Conjunction.tca <= horizon_72h)
        )
    ) or 0
    high_risk_24h = (
        await session.scalar(
            select(func.count())
            .select_from(Conjunction)
            .where(
                Conjunction.tca >= now,
                Conjunction.tca <= horizon_24h,
                Conjunction.miss_distance_km < 1.0,
            )
        )
    ) or 0
    return StatsResponse(
        total_satellites=int(total_satellites),
        total_active=int(total_active),
        tle_last_updated=last_updated,
        conjunctions_24h=int(conj_24h),
        conjunctions_72h=int(conj_72h),
        high_risk_24h=int(high_risk_24h),
    )
