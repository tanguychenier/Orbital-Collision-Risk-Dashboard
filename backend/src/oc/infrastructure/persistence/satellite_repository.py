"""SQLAlchemy adapter for the satellite repository port.

This adapter owns every read-only operation the public API uses to
expose satellite metadata. Writes still flow through
:class:`oc.infrastructure.persistence.tle_repository.SQLAlchemyTLERepository`
because TLE ingestion creates the parent satellite rows as a side
effect.
"""

from __future__ import annotations

from collections.abc import Sequence

from sqlalchemy import ColumnElement, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from oc.domain.entities import SatelliteRecord, TLERecord
from oc.infrastructure.persistence.models import TLE, Satellite


def _to_record(sat: Satellite) -> SatelliteRecord:
    """Translate an ORM ``Satellite`` row to its domain ``SatelliteRecord``."""
    return SatelliteRecord(
        norad_id=sat.norad_id,
        name=sat.name,
        country=sat.country,
        object_type=sat.object_type,
        launch_date=sat.launch_date,
        is_active=sat.is_active,
    )


def _to_tle_record(tle: TLE) -> TLERecord:
    """Translate an ORM ``TLE`` row to its domain ``TLERecord``."""
    return TLERecord(
        norad_id=tle.norad_id,
        epoch=tle.epoch,
        line1=tle.line1,
        line2=tle.line2,
        db_id=tle.id,
    )


class SQLAlchemySatelliteRepository:
    """Implements :class:`oc.application.ports.SatelliteRepository`."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def find_by_identifier(
        self, identifier: str
    ) -> tuple[SatelliteRecord, TLERecord | None] | None:
        """Resolve a NORAD id (digits) or exact name to a satellite + last TLE."""
        stmt = select(Satellite)
        if identifier.isdigit():
            stmt = stmt.where(Satellite.norad_id == int(identifier))
        else:
            stmt = stmt.where(func.lower(Satellite.name) == identifier.lower())
        sat = (await self._session.execute(stmt)).scalar_one_or_none()
        if sat is None:
            return None
        latest_tle = await self._session.execute(
            select(TLE).where(TLE.norad_id == sat.norad_id).order_by(TLE.epoch.desc()).limit(1)
        )
        tle_row = latest_tle.scalar_one_or_none()
        return _to_record(sat), (_to_tle_record(tle_row) if tle_row is not None else None)

    async def search(self, query: str | None, limit: int) -> Sequence[SatelliteRecord]:
        """Return up to ``limit`` satellites matching ``query`` (fuzzy name or exact id)."""
        normalised = (query or "").strip()
        if not normalised:
            stmt = select(Satellite).order_by(Satellite.norad_id).limit(limit)
        else:
            like = f"%{normalised.lower()}%"
            conditions: list[ColumnElement[bool]] = [func.lower(Satellite.name).like(like)]
            if normalised.isdigit():
                conditions.append(Satellite.norad_id == int(normalised))
            stmt = (
                select(Satellite)
                .where(or_(*conditions))
                .order_by(Satellite.norad_id)
                .limit(limit)
            )
        rows = (await self._session.execute(stmt)).scalars().all()
        return [_to_record(sat) for sat in rows]
