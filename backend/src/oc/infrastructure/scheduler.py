"""APScheduler outbound adapter.

Boots periodic TLE ingestion and conjunction recomputation jobs. The
job *bodies* live in :mod:`oc.application.use_cases` -- this module only
wires them to the scheduler trigger and provides the SQLAlchemy session
context to the use cases.
"""

from __future__ import annotations

import logging
import uuid
from collections.abc import Sequence
from datetime import UTC, datetime, timedelta

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession

from oc.application.use_cases.alerts import notify_pending_alerts
from oc.application.use_cases.compute_conjunctions import (
    ScreeningParameters,
    screen_population,
)
from oc.application.use_cases.refresh_tles import refresh_tles_from_url
from oc.config import Settings, get_settings
from oc.db import session_scope
from oc.domain.entities import ConjunctionEvent, SatelliteState
from oc.infrastructure.notifications import build_default_notifier
from oc.infrastructure.numerics import ScipyBoundedMinimizer
from oc.infrastructure.persistence import (
    SQLAlchemyAlertSubscriptionRepository,
    SQLAlchemyConjunctionAlertSource,
    SQLAlchemyTLERepository,
)
from oc.infrastructure.persistence.models import Conjunction
from oc.infrastructure.propagation import SGP4Propagator
from oc.infrastructure.tle_sources import CelestrakTLESource

logger = logging.getLogger(__name__)


async def refresh_tles_job(settings: Settings | None = None) -> None:
    """Fetch the configured CelesTrak catalogs and persist new TLEs."""
    s = settings or get_settings()
    async with session_scope() as session:
        try:
            source = CelestrakTLESource(timeout_seconds=s.http_timeout_seconds)
            repository = SQLAlchemyTLERepository(session)
            await refresh_tles_from_url(source, repository, s.celestrak_url)
        except Exception as exc:
            logger.error(
                "tle refresh failed",
                extra={"url": s.celestrak_url, "error": str(exc)},
            )


async def recompute_conjunctions_job(settings: Settings | None = None) -> None:
    """Recompute conjunctions over the configured horizon."""
    s = settings or get_settings()
    now = datetime.now(UTC)
    horizon = now + timedelta(hours=s.screening_horizon_hours)
    propagator = SGP4Propagator()
    minimizer = ScipyBoundedMinimizer()

    async with session_scope() as session:
        repository = SQLAlchemyTLERepository(session)
        states = _build_states_from_repository(propagator, await _latest_states(repository))
        if len(states) < 2:
            logger.info("conjunctions recompute: not enough satellites", extra={"n": len(states)})
            return

        parameters = ScreeningParameters(
            coarse_step_seconds=s.screening_coarse_step_seconds,
            fine_step_seconds=s.screening_fine_step_seconds,
            perigee_apogee_buffer_km=s.screening_perigee_apogee_buffer_km,
            distance_threshold_km=s.screening_distance_threshold_km,
            probability_sigma_km=s.probability_sigma_km,
            max_pairs=s.screening_max_pairs,
        )
        events = screen_population(propagator, minimizer, states, now, horizon, parameters)
        await persist_events(session, events, repository)
        logger.info("conjunctions recompute complete", extra={"count": len(events)})


async def _latest_states(
    repository: SQLAlchemyTLERepository,
) -> Sequence[tuple[int, str, str, str, int | None]]:
    """Return ``(norad_id, name, line1, line2, tle_db_id)`` tuples for active satellites."""
    rows = await repository.latest_tle_per_active_satellite()
    return [(s.norad_id, s.name, t.line1, t.line2, t.db_id) for s, t in rows]


def _build_states_from_repository(
    propagator: SGP4Propagator,
    rows: Sequence[tuple[int, str, str, str, int | None]],
) -> list[SatelliteState]:
    """Compile each row into a :class:`SatelliteState` with a precompiled propagator state."""
    states: list[SatelliteState] = []
    for norad_id, name, line1, line2, tle_db_id in rows:
        states.append(
            SatelliteState(
                norad_id=norad_id,
                name=name,
                line1=line1,
                line2=line2,
                satrec=propagator.build_state(line1, line2),
                tle_db_id=tle_db_id,
            )
        )
    return states


async def persist_events(
    session: AsyncSession,
    events: Sequence[ConjunctionEvent],
    repository: SQLAlchemyTLERepository,
) -> None:
    """Replace the conjunctions table contents with ``events``."""
    await session.execute(delete(Conjunction))
    for ev in events:
        tle_a_id = ev.sat_a.tle_db_id or await repository.find_latest_tle_id(ev.sat_a.norad_id)
        tle_b_id = ev.sat_b.tle_db_id or await repository.find_latest_tle_id(ev.sat_b.norad_id)
        if tle_a_id is None or tle_b_id is None:
            continue
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


async def notify_pending_alerts_job(settings: Settings | None = None) -> None:
    """Deliver pending alerts to every active subscription."""
    s = settings or get_settings()
    notifier = build_default_notifier(s)
    async with session_scope() as session:
        repository = SQLAlchemyAlertSubscriptionRepository(session)
        source = SQLAlchemyConjunctionAlertSource(session)
        try:
            delivered = await notify_pending_alerts(
                now=datetime.now(UTC),
                repository=repository,
                source=source,
                notifier=notifier,
                horizon_days=s.alerts_horizon_days,
            )
            logger.info("alerts notify complete", extra={"delivered": delivered})
        except Exception as exc:
            logger.error("alerts notify failed", extra={"error": str(exc)})


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
    scheduler.add_job(
        notify_pending_alerts_job,
        trigger=IntervalTrigger(minutes=s.alerts_notify_interval_minutes),
        id="notify_pending_alerts",
        name="Alert notification dispatch",
        max_instances=1,
        coalesce=True,
    )
    return scheduler
