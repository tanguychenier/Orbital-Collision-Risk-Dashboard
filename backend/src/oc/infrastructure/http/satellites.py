"""``/api/satellites`` endpoint."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy import Select, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from oc.config import Settings, get_settings
from oc.db import get_db_session
from oc.infrastructure.persistence.models import Satellite
from oc.interface.schemas import SatelliteDetail

router = APIRouter()


@router.get(
    "/satellites",
    response_model=list[SatelliteDetail],
    response_model_by_alias=True,
)
async def list_satellites(
    q: str | None = Query(default=None, description="Optional case-insensitive name filter."),
    limit: int = Query(default=50, ge=1, le=1000),
    offset: int = Query(default=0, ge=0),
    session: AsyncSession = Depends(get_db_session),
    settings: Settings = Depends(get_settings),
) -> list[SatelliteDetail]:
    """Return a paginated, optionally filtered satellite list."""
    capped_limit = min(limit, settings.api_max_limit)
    stmt = _apply_name_filter(select(Satellite).order_by(Satellite.norad_id), q)
    stmt = stmt.offset(offset).limit(capped_limit)
    sats = (await session.execute(stmt)).scalars().all()
    return [SatelliteDetail.model_validate(s, from_attributes=True) for s in sats]


def _apply_name_filter(
    stmt: Select[tuple[Satellite]], query: str | None
) -> Select[tuple[Satellite]]:
    """Return ``stmt`` narrowed by a case-insensitive ``LIKE`` on ``Satellite.name``."""
    if not query:
        return stmt
    like = f"%{query.lower()}%"
    return stmt.where(func.lower(Satellite.name).like(like))
