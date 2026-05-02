"""``/api/conjunctions`` endpoints."""

from __future__ import annotations

import csv
import io
import logging
from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from oc.config import Settings, get_settings
from oc.db import get_db_session
from oc.infrastructure.persistence.models import TLE, Conjunction
from oc.infrastructure.propagation.geodetic import ecef_to_geodetic, teme_to_ecef
from oc.infrastructure.propagation.sgp4_propagator import (
    PropagationError,
    propagate_single,
    satrec_from_tle,
)
from oc.interface.schemas import (
    ConjunctionDetail,
    ConjunctionListItem,
    GeodeticTCAPosition,
    SatelliteDetail,
    SatelliteSummary,
)

_log = logging.getLogger(__name__)

# Default upper bound on the screening horizon exposed via the ``hours``
# query parameter. Accepting up to a month protects callers from foot
# guns while still covering the typical 72 h operational window.
_MAX_HORIZON_HOURS: float = 24.0 * 30.0
_DEFAULT_HORIZON_HOURS: float = 72.0
_DEFAULT_MAX_DISTANCE_KM: float = 5.0
_DEFAULT_LIMIT: int = 200
_MAX_LIMIT: int = 1000

router = APIRouter()


def _ensure_utc(dt: datetime) -> datetime:
    """Return ``dt`` re-tagged as UTC if naive, otherwise unchanged."""
    return dt if dt.tzinfo is not None else dt.replace(tzinfo=UTC)


@router.get("/conjunctions", response_model=list[ConjunctionListItem])
async def list_conjunctions(
    max_distance_km: float = Query(default=_DEFAULT_MAX_DISTANCE_KM, gt=0.0, le=1000.0),
    hours: float = Query(default=_DEFAULT_HORIZON_HOURS, gt=0.0, le=_MAX_HORIZON_HOURS),
    limit: int = Query(default=_DEFAULT_LIMIT, ge=1, le=_MAX_LIMIT),
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
        .options(
            selectinload(Conjunction.sat_a),
            selectinload(Conjunction.sat_b),
            selectinload(Conjunction.tle_a),
            selectinload(Conjunction.tle_b),
        )
        .where(
            Conjunction.tca >= now,
            Conjunction.tca <= horizon,
            Conjunction.miss_distance_km <= max_distance_km,
        )
        .order_by(Conjunction.tca)
        .offset(offset)
        .limit(capped_limit)
    )
    rows = (await session.execute(stmt)).scalars().all()
    return [_to_list_item(c) for c in rows]


@router.get(
    "/conjunctions.csv",
    responses={200: {"content": {"text/csv": {}}}},
)
async def export_conjunctions_csv(
    max_distance_km: float = Query(default=_DEFAULT_MAX_DISTANCE_KM, gt=0.0, le=1000.0),
    hours: float = Query(default=_DEFAULT_HORIZON_HOURS, gt=0.0, le=_MAX_HORIZON_HOURS),
    norad_id: list[int] | None = Query(default=None),
    session: AsyncSession = Depends(get_db_session),
    settings: Settings = Depends(get_settings),
) -> StreamingResponse:
    """Stream upcoming conjunctions as a UTF-8 CSV file.

    Designed for ops teams: open in Excel / LibreOffice / pandas. The
    column set mirrors the JSON list payload one-to-one (one row per
    conjunction) and includes the WGS-84 sub-satellite points so an
    operator can sanity-check the report against a separate STK or
    GMAT pipeline.
    """
    now = datetime.now(UTC)
    horizon = now + timedelta(hours=hours)
    stmt = (
        select(Conjunction)
        .options(
            selectinload(Conjunction.sat_a),
            selectinload(Conjunction.sat_b),
            selectinload(Conjunction.tle_a),
            selectinload(Conjunction.tle_b),
        )
        .where(
            Conjunction.tca >= now,
            Conjunction.tca <= horizon,
            Conjunction.miss_distance_km <= max_distance_km,
        )
        .order_by(Conjunction.tca)
        .limit(min(10_000, settings.api_max_limit * 10))
    )
    if norad_id:
        from sqlalchemy import or_

        stmt = stmt.where(
            or_(
                Conjunction.sat_a_norad_id.in_(norad_id),
                Conjunction.sat_b_norad_id.in_(norad_id),
            )
        )
    rows = (await session.execute(stmt)).scalars().all()

    buf = io.StringIO()
    writer = csv.writer(buf, lineterminator="\n")
    writer.writerow(
        [
            "id",
            "tca_utc",
            "miss_distance_km",
            "relative_velocity_km_s",
            "probability",
            "sat_a_norad_id",
            "sat_a_name",
            "sat_a_lat_deg",
            "sat_a_lon_deg",
            "sat_a_alt_km",
            "sat_b_norad_id",
            "sat_b_name",
            "sat_b_lat_deg",
            "sat_b_lon_deg",
            "sat_b_alt_km",
        ]
    )
    for c in rows:
        tca = _ensure_utc(c.tca)
        pa = _propagate_to_geodetic(c.tle_a, tca)
        pb = _propagate_to_geodetic(c.tle_b, tca)
        writer.writerow(
            [
                c.id,
                tca.isoformat(),
                f"{c.miss_distance_km:.4f}",
                f"{c.relative_velocity_km_s:.4f}",
                f"{c.probability:.6e}",
                c.sat_a.norad_id,
                c.sat_a.name,
                f"{pa.latitude_deg:.6f}" if pa else "",
                f"{pa.longitude_deg:.6f}" if pa else "",
                f"{pa.altitude_km:.3f}" if pa else "",
                c.sat_b.norad_id,
                c.sat_b.name,
                f"{pb.latitude_deg:.6f}" if pb else "",
                f"{pb.longitude_deg:.6f}" if pb else "",
                f"{pb.altitude_km:.3f}" if pb else "",
            ]
        )
    buf.seek(0)
    return StreamingResponse(
        iter([buf.getvalue()]),
        media_type="text/csv; charset=utf-8",
        headers={
            "Content-Disposition": 'attachment; filename="conjunctions.csv"',
            "Cache-Control": "public, max-age=300",
        },
    )


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
    row = (await session.execute(stmt)).scalar_one_or_none()
    if row is None:
        raise HTTPException(status_code=404, detail="conjunction not found")
    return _to_detail(row)


def _propagate_to_geodetic(tle: TLE, tca: datetime) -> GeodeticTCAPosition | None:
    """Propagate a TLE to ``tca`` and return the WGS-84 sub-satellite point.

    Returns ``None`` instead of raising so that one corrupt TLE never
    breaks the whole list. The endpoint logs the failure and the
    front-end falls back to an unobtrusive null marker.
    """
    try:
        satrec = satrec_from_tle(tle.line1, tle.line2)
        position_teme_km, _velocity = propagate_single(satrec, _ensure_utc(tca))
    except (PropagationError, ValueError, RuntimeError) as exc:
        _log.warning("skipping TCA position for tle %d: %s", tle.id, exc, exc_info=False)
        return None
    ecef = teme_to_ecef(position_teme_km, _ensure_utc(tca))
    lat, lon, alt = ecef_to_geodetic(ecef)
    return GeodeticTCAPosition(latitude_deg=lat, longitude_deg=lon, altitude_km=alt)


def _to_list_item(c: Conjunction) -> ConjunctionListItem:
    """Map a SQLAlchemy ``Conjunction`` row to its list-item DTO."""
    tca = _ensure_utc(c.tca)
    return ConjunctionListItem(
        id=c.id,
        sat_a=SatelliteSummary(norad_id=c.sat_a.norad_id, name=c.sat_a.name),
        sat_b=SatelliteSummary(norad_id=c.sat_b.norad_id, name=c.sat_b.name),
        tca=tca,
        miss_distance_km=c.miss_distance_km,
        relative_velocity_km_s=c.relative_velocity_km_s,
        probability=c.probability,
        computed_at=_ensure_utc(c.computed_at),
        tca_position_a=_propagate_to_geodetic(c.tle_a, tca),
        tca_position_b=_propagate_to_geodetic(c.tle_b, tca),
    )


def _to_detail(c: Conjunction) -> ConjunctionDetail:
    """Map a SQLAlchemy ``Conjunction`` row to its detail DTO."""
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
