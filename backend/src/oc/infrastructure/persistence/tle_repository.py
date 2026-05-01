"""SQLAlchemy adapter for the TLE repository port."""

from __future__ import annotations

from collections.abc import Iterable, Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from oc.domain.entities import ParsedTLE, SatelliteRecord, TLERecord
from oc.infrastructure.persistence.models import TLE, Satellite


class SQLAlchemyTLERepository:
    """Implements :class:`oc.application.ports.TLERepository` against SQLAlchemy."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def upsert_parsed_tles(self, parsed: Iterable[ParsedTLE]) -> tuple[int, int]:
        """Persist parsed TLEs idempotently. Returns ``(satellites_added, tles_added)``."""
        sats_added = 0
        tles_added = 0
        for record in parsed:
            sats_added += await self._upsert_satellite(record)
            tles_added += await self._insert_tle_if_new(record)
        await self._session.flush()
        return sats_added, tles_added

    async def latest_tle_per_active_satellite(
        self,
    ) -> Sequence[tuple[SatelliteRecord, TLERecord]]:
        """Return the most recent TLE for every active satellite."""
        stmt = (
            select(Satellite)
            .options(selectinload(Satellite.tles))
            .where(Satellite.is_active.is_(True))
        )
        rows = (await self._session.execute(stmt)).scalars().all()
        out: list[tuple[SatelliteRecord, TLERecord]] = []
        for sat in rows:
            if not sat.tles:
                continue
            tle = sat.tles[0]
            out.append(
                (
                    SatelliteRecord(
                        norad_id=sat.norad_id,
                        name=sat.name,
                        country=sat.country,
                        object_type=sat.object_type,
                        launch_date=sat.launch_date,
                        is_active=sat.is_active,
                    ),
                    TLERecord(
                        norad_id=tle.norad_id,
                        epoch=tle.epoch,
                        line1=tle.line1,
                        line2=tle.line2,
                        db_id=tle.id,
                    ),
                )
            )
        return out

    async def find_latest_tle_id(self, norad_id: int) -> int | None:
        """Return the database id of the most recent TLE for ``norad_id`` or ``None``."""
        stmt = select(TLE.id).where(TLE.norad_id == norad_id).order_by(TLE.epoch.desc()).limit(1)
        result = await self._session.scalar(stmt)
        return int(result) if result is not None else None

    async def _upsert_satellite(self, record: ParsedTLE) -> int:
        """Insert or update the parent ``Satellite`` row. Returns ``1`` if created."""
        sat = await self._session.get(Satellite, record.norad_id)
        if sat is None:
            self._session.add(Satellite(norad_id=record.norad_id, name=record.name, is_active=True))
            return 1
        if sat.name != record.name:
            sat.name = record.name
        sat.is_active = True
        return 0

    async def _insert_tle_if_new(self, record: ParsedTLE) -> int:
        """Insert the TLE row when ``(norad_id, epoch)`` is unseen. Returns ``1`` if inserted."""
        existing = await self._session.execute(
            select(TLE).where(TLE.norad_id == record.norad_id, TLE.epoch == record.epoch)
        )
        if existing.scalar_one_or_none() is not None:
            return 0
        self._session.add(
            TLE(
                norad_id=record.norad_id,
                epoch=record.epoch,
                line1=record.line1,
                line2=record.line2,
            )
        )
        return 1
