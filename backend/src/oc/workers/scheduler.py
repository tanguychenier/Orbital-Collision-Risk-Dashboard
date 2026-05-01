"""Backwards-compatibility shim. See :mod:`oc.infrastructure.scheduler`."""

from oc.infrastructure.scheduler import (
    build_scheduler,
    notify_pending_alerts_job,
    persist_events,
    recompute_conjunctions_job,
    refresh_tles_job,
)

__all__ = [
    "build_scheduler",
    "notify_pending_alerts_job",
    "persist_events",
    "recompute_conjunctions_job",
    "refresh_tles_job",
]
