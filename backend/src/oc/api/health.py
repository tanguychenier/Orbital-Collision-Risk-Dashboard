"""``/api/health`` endpoint."""

from __future__ import annotations

from datetime import UTC, datetime

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from oc.config import Settings, get_settings
from oc.db import get_db_session
from oc.models import TLE
from oc.schemas import HealthResponse

router = APIRouter()


@router.get("/health", response_model=HealthResponse)
async def health(
    session: AsyncSession = Depends(get_db_session),
    settings: Settings = Depends(get_settings),
) -> HealthResponse:
    """Liveness probe with TLE freshness indicator."""
    result = await session.execute(select(func.max(TLE.epoch)))
    latest = result.scalar_one_or_none()
    age_hours: float | None = None
    if latest is not None:
        if latest.tzinfo is None:
            latest = latest.replace(tzinfo=UTC)
        age_hours = (datetime.now(UTC) - latest).total_seconds() / 3600.0
    return HealthResponse(status="ok", version=settings.version, tle_age_hours=age_hours)
