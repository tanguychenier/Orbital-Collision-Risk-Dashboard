"""Aggregate ``APIRouter`` mounting every domain router under ``/api``."""

from __future__ import annotations

from fastapi import APIRouter

from oc.infrastructure.http import (
    alerts,
    conjunctions,
    health,
    heatmap,
    satellites,
    stats,
)


def build_api_router() -> APIRouter:
    """Build the parent router with every domain router mounted under ``/api``."""
    router = APIRouter(prefix="/api")
    router.include_router(health.router, tags=["health"])
    router.include_router(stats.router, tags=["stats"])
    router.include_router(satellites.router, tags=["satellites"])
    router.include_router(conjunctions.router, tags=["conjunctions"])
    router.include_router(heatmap.router, tags=["heatmap"])
    router.include_router(alerts.router, tags=["alerts"])
    return router
