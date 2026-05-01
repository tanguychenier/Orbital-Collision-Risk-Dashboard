"""APScheduler jobs for periodic TLE ingestion and conjunction recomputation."""

from __future__ import annotations

import uuid
from collections.abc import Sequence
from datetime import UTC, datetime, timedelta

import structlog
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from oc.config import Settings, get_settings
from oc.db import session_scope
from oc.models import TLE, Conjunction, Satellite
from oc.services.conjunctions import (
    ConjunctionEvent,
    SatelliteState,
    screen_population,
)
from oc.services.tle_fetcher import ingest_url

logger = structlog.get_logger(__name__)


async def refresh_tles_job(settings: Settings | None = None) -> None:
    """Fetch the configured CelesTrak catalogs and persist new TLEs."""
    s = settings or get_settings()
    async with session_scope() as session:
        try:
            await ingest_url(session, s.celestrak_url, settings=s)
        except Exception as exc:
            logger.error("tle refresh failed", url=s.celestrak_url, error=str(exc))


async def recompute_conjunctions_job(settings: Settings | None = None) -> None:
    """Recompute conjunctions over the configured horizon."""
    s = settings or get_settings()
    now = datetime.now(UTC)
    horizon = now + timedelta(hours=s.screening_horizon_hours)

    async with session_scope() as session:
        # Pick the most recent TLE per satellite.
        stmt = (
            select(Satellite)
            .options(selectinload(Satellite.tles))
            .where(Satellite.is_active.is_(True))
        )
        sats = (await session.execute(stmt)).scalars().all()
        states: list[SatelliteState] = []
        for sat in sats:
            if not sat.tles:
                continue
            tle = sat.tles[0]
            states.append(
                SatelliteState.from_tle(
                    norad_id=sat.norad_id,
                    name=sat.name,
                    line1=tle.line1,
                    line2=tle.line2,
                    tle_db_id=tle.id,
                )
            )

        if len(states) < 2:
            logger.info("conjunctions recompute: not enough satellites", n=len(states))
            return

        events = screen_population(
            states,
            now,
            horizon,
            coarse_step_seconds=s.screening_coarse_step_seconds,
            fine_step_seconds=s.screening_fine_step_seconds,
            perigee_apogee_buffer_km=s.screening_perigee_apogee_buffer_km,
            distance_threshold_km=s.screening_distance_threshold_km,
            probability_sigma_km=s.probability_sigma_km,
            max_pairs=s.screening_max_pairs,
        )
        await persist_events(session, events)
        logger.info("conjunctions recompute complete", count=len(events))


async def persist_events(session: AsyncSession, events: Sequence[ConjunctionEvent]) -> None:
    """Replace the conjunctions table contents with ``events``."""
    await session.execute(delete(Conjunction))
    for ev in events:
        if ev.sat_a.tle_db_id is None or ev.sat_b.tle_db_id is None:
            tle_a_id = await _lookup_tle_id(session, ev.sat_a.norad_id)
            tle_b_id = await _lookup_tle_id(session, ev.sat_b.norad_id)
            if tle_a_id is None or tle_b_id is None:
                continue
        else:
            tle_a_id = ev.sat_a.tle_db_id
            tle_b_id = ev.sat_b.tle_db_id
        session.add(
            Conjunction(
                id=ev.id or uuid.uuid4().hex,
                sat_a_norad_id=ev.sat_a.norad_id,
                sat_b_norad_id=ev.sat_b.norad_id,
                tle_a_id=tle_a_id,
                tle_b_id=tle_b_id,
                tca=ev.tca,
                miss_distance_km=ev.miss_distance_km,
                relative_velocity_km_s=ev.relative_velocity_km_s,
                probability=ev.probability,
            )
        )


async def _lookup_tle_id(session: AsyncSession, norad_id: int) -> int | None:
    """Return the id of the most recent TLE for ``norad_id``."""
    stmt = select(TLE.id).where(TLE.norad_id == norad_id).order_by(TLE.epoch.desc()).limit(1)
    result = await session.scalar(stmt)
    return int(result) if result is not None else None


def build_scheduler(settings: Settings | None = None) -> AsyncIOScheduler:
    """Build (but do not start) an :class:`AsyncIOScheduler` with the jobs."""
    s = settings or get_settings()
    scheduler = AsyncIOScheduler(timezone="UTC")
    scheduler.add_job(
        refresh_tles_job,
        trigger=IntervalTrigger(hours=s.tle_refresh_interval_hours),
        id="refresh_tles",
        name="TLE refresh",
        max_instances=1,
        coalesce=True,
    )
    scheduler.add_job(
        recompute_conjunctions_job,
        trigger=IntervalTrigger(minutes=s.conjunction_refresh_interval_minutes),
        id="recompute_conjunctions",
        name="Conjunction recompute",
        max_instances=1,
        coalesce=True,
    )
    return scheduler
