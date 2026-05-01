"""``/api/stats`` endpoint."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Depends
from sqlalchemy import Select, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from oc.db import get_db_session
from oc.infrastructure.persistence.models import TLE, Conjunction, Satellite
from oc.interface.schemas import StatsResponse

# Threshold below which a conjunction is considered "high risk" for the
# ``high_risk_24h`` count. One kilometre is the operationally-recognised
# triage threshold for screening tools.
_HIGH_RISK_MISS_THRESHOLD_KM: float = 1.0
_HOURS_24: float = 24.0
_HOURS_72: float = 72.0

router = APIRouter()


@router.get("/stats", response_model=StatsResponse)
async def stats(session: AsyncSession = Depends(get_db_session)) -> StatsResponse:
    """Population, ingestion freshness, and conjunction counts."""
    now = datetime.now(UTC)
    horizon_24h = now + timedelta(hours=_HOURS_24)
    horizon_72h = now + timedelta(hours=_HOURS_72)

    total_satellites = await _count(session, select(func.count()).select_from(Satellite))
    total_active = await _count(
        session,
        select(func.count()).select_from(Satellite).where(Satellite.is_active.is_(True)),
    )
    last_updated = await session.scalar(select(func.max(TLE.epoch)))
    if last_updated is not None and last_updated.tzinfo is None:
        last_updated = last_updated.replace(tzinfo=UTC)

    conj_24h = await _count_conjunctions_within(session, now, horizon_24h)
    conj_72h = await _count_conjunctions_within(session, now, horizon_72h)
    high_risk_24h = await _count(
        session,
        select(func.count())
        .select_from(Conjunction)
        .where(
            Conjunction.tca >= now,
            Conjunction.tca <= horizon_24h,
            Conjunction.miss_distance_km < _HIGH_RISK_MISS_THRESHOLD_KM,
        ),
    )
    return StatsResponse(
        total_satellites=total_satellites,
        total_active=total_active,
        tle_last_updated=last_updated,
        conjunctions_24h=conj_24h,
        conjunctions_72h=conj_72h,
        high_risk_24h=high_risk_24h,
    )


async def _count(session: AsyncSession, stmt: Select[tuple[int]]) -> int:
    """Run a ``SELECT count(*) ...`` and coerce ``NULL`` to ``0``."""
    raw = await session.scalar(stmt)
    return int(raw or 0)


async def _count_conjunctions_within(
    session: AsyncSession, lower: datetime, upper: datetime
) -> int:
    """Count rows in ``conjunctions`` with ``tca`` in ``[lower, upper]``."""
    stmt = (
        select(func.count())
        .select_from(Conjunction)
        .where(Conjunction.tca >= lower, Conjunction.tca <= upper)
    )
    return await _count(session, stmt)
