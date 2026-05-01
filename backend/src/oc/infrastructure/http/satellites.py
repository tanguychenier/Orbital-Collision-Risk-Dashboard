"""``/api/satellites`` endpoints."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import Select, case, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from oc.config import Settings, get_settings
from oc.db import get_db_session
from oc.infrastructure.persistence.models import Conjunction, Satellite
from oc.infrastructure.persistence.satellite_repository import SQLAlchemySatelliteRepository
from oc.interface.schemas import (
    ConjunctionListItem,
    SatelliteConjunctionStats,
    SatelliteDetail,
    SatelliteDetailResponse,
    SatelliteSummary,
)

# Default upper bound on the screening horizon exposed by the endpoint
# returning a satellite's conjunctions. Mirrors the dashboard cap so a
# UI request for "next month" never silently truncates.
_MAX_HORIZON_HOURS: float = 24.0 * 30.0
_DEFAULT_HORIZON_HOURS: float = 168.0
_DEFAULT_SAT_LIST_LIMIT: int = 50
_DEFAULT_SEARCH_LIMIT: int = 20
_MAX_SEARCH_LIMIT: int = 100
_DEFAULT_CONJUNCTIONS_LIMIT: int = 200
_MAX_CONJUNCTIONS_LIMIT: int = 1000

# Window sizes for the small summary card shown on the satellite detail
# page. Centralised so the schema, the API and the UI agree on the same
# rolling windows.
_WINDOW_24H = timedelta(hours=24)
_WINDOW_72H = timedelta(hours=72)
_WINDOW_7D = timedelta(days=7)

router = APIRouter()


def _ensure_utc(dt: datetime) -> datetime:
    """Return ``dt`` re-tagged as UTC if naive, otherwise unchanged."""
    return dt if dt.tzinfo is not None else dt.replace(tzinfo=UTC)


@router.get(
    "/satellites",
    response_model=list[SatelliteDetail],
    response_model_by_alias=True,
)
async def list_satellites(
    q: str | None = Query(default=None, description="Optional case-insensitive name filter."),
    limit: int = Query(default=_DEFAULT_SAT_LIST_LIMIT, ge=1, le=1000),
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


@router.get(
    "/satellites/search",
    response_model=list[SatelliteDetail],
    response_model_by_alias=True,
)
async def search_satellites(
    q: str | None = Query(default=None, description="Free-text search on name or NORAD id."),
    limit: int = Query(default=_DEFAULT_SEARCH_LIMIT, ge=1, le=_MAX_SEARCH_LIMIT),
    session: AsyncSession = Depends(get_db_session),
) -> list[SatelliteDetail]:
    """Return up to ``limit`` satellites matching ``q`` (fuzzy name or exact NORAD id)."""
    repo = SQLAlchemySatelliteRepository(session)
    matches = await repo.search(q, limit)
    return [SatelliteDetail.model_validate(record, from_attributes=True) for record in matches]


@router.get(
    "/satellites/{identifier}",
    response_model=SatelliteDetailResponse,
    response_model_by_alias=True,
)
async def get_satellite(
    identifier: str,
    session: AsyncSession = Depends(get_db_session),
) -> SatelliteDetailResponse:
    """Return the satellite record + last TLE epoch + rolling conjunction counts."""
    repo = SQLAlchemySatelliteRepository(session)
    found = await repo.find_by_identifier(identifier)
    if found is None:
        raise HTTPException(status_code=404, detail="satellite not found")
    record, last_tle = found
    now = datetime.now(UTC)
    counts = await _conjunction_counts(session, record.norad_id, now)
    return SatelliteDetailResponse(
        satellite=SatelliteDetail.model_validate(record, from_attributes=True),
        last_tle_epoch=_ensure_utc(last_tle.epoch) if last_tle is not None else None,
        stats=counts,
    )


@router.get(
    "/satellites/{identifier}/conjunctions",
    response_model=list[ConjunctionListItem],
)
async def list_satellite_conjunctions(
    identifier: str,
    hours: float = Query(default=_DEFAULT_HORIZON_HOURS, gt=0.0, le=_MAX_HORIZON_HOURS),
    limit: int = Query(default=_DEFAULT_CONJUNCTIONS_LIMIT, ge=1, le=_MAX_CONJUNCTIONS_LIMIT),
    offset: int = Query(default=0, ge=0),
    session: AsyncSession = Depends(get_db_session),
    settings: Settings = Depends(get_settings),
) -> list[ConjunctionListItem]:
    """Return upcoming conjunctions where this satellite appears as A or B, sorted by TCA."""
    repo = SQLAlchemySatelliteRepository(session)
    found = await repo.find_by_identifier(identifier)
    if found is None:
        raise HTTPException(status_code=404, detail="satellite not found")
    record, _ = found
    norad_id = record.norad_id
    now = datetime.now(UTC)
    horizon = now + timedelta(hours=hours)
    capped_limit = min(limit, settings.api_max_limit)
    stmt = (
        select(Conjunction)
        .options(selectinload(Conjunction.sat_a), selectinload(Conjunction.sat_b))
        .where(
            or_(
                Conjunction.sat_a_norad_id == norad_id,
                Conjunction.sat_b_norad_id == norad_id,
            ),
            Conjunction.tca >= now,
            Conjunction.tca <= horizon,
        )
        .order_by(Conjunction.tca)
        .offset(offset)
        .limit(capped_limit)
    )
    rows = (await session.execute(stmt)).scalars().all()
    return [_to_list_item(c) for c in rows]


def _apply_name_filter(
    stmt: Select[tuple[Satellite]], query: str | None
) -> Select[tuple[Satellite]]:
    """Return ``stmt`` narrowed by a case-insensitive ``LIKE`` on ``Satellite.name``."""
    if not query:
        return stmt
    like = f"%{query.lower()}%"
    return stmt.where(func.lower(Satellite.name).like(like))


def _to_list_item(c: Conjunction) -> ConjunctionListItem:
    """Map a SQLAlchemy ``Conjunction`` row to its list-item DTO."""
    return ConjunctionListItem(
        id=c.id,
        sat_a=SatelliteSummary(norad_id=c.sat_a.norad_id, name=c.sat_a.name),
        sat_b=SatelliteSummary(norad_id=c.sat_b.norad_id, name=c.sat_b.name),
        tca=_ensure_utc(c.tca),
        miss_distance_km=c.miss_distance_km,
        relative_velocity_km_s=c.relative_velocity_km_s,
        probability=c.probability,
        computed_at=_ensure_utc(c.computed_at),
    )


async def _conjunction_counts(
    session: AsyncSession, norad_id: int, now: datetime
) -> SatelliteConjunctionStats:
    """Count upcoming conjunctions involving ``norad_id`` over 24h, 72h and 7d windows."""
    stmt = select(
        func.coalesce(func.sum(_within(now, _WINDOW_24H)), 0).label("c24"),
        func.coalesce(func.sum(_within(now, _WINDOW_72H)), 0).label("c72"),
        func.coalesce(func.sum(_within(now, _WINDOW_7D)), 0).label("c7d"),
    ).where(
        or_(
            Conjunction.sat_a_norad_id == norad_id,
            Conjunction.sat_b_norad_id == norad_id,
        ),
        Conjunction.tca >= now,
    )
    row = (await session.execute(stmt)).one()
    return SatelliteConjunctionStats(
        next_24h=int(row.c24 or 0),
        next_72h=int(row.c72 or 0),
        next_7d=int(row.c7d or 0),
    )


def _within(now: datetime, window: timedelta) -> object:
    """Build a ``CASE`` expression returning ``1`` when ``tca`` is inside ``[now, now+window]``."""
    horizon = now + window
    return case((Conjunction.tca <= horizon, 1), else_=0)
