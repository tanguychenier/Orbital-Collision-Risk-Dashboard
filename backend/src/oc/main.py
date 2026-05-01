"""FastAPI application factory."""

from __future__ import annotations

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Any

import structlog
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from oc import __version__
from oc.api import conjunctions, health, satellites, stats
from oc.config import Settings, get_settings
from oc.db import init_models


def configure_logging() -> None:
    """Configure structlog for JSON-style structured output."""
    logging.basicConfig(format="%(message)s", level=logging.INFO, force=True)
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso", utc=True),
            structlog.processors.JSONRenderer(),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(logging.INFO),
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )


def create_app(settings: Settings | None = None) -> FastAPI:
    """Build a FastAPI app instance.

    Args:
        settings: Optional settings override (used by tests).
    """
    configure_logging()
    s = settings or get_settings()

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        await init_models()
        scheduler: Any | None = None
        if s.enable_scheduler:
            from oc.workers.scheduler import build_scheduler

            scheduler = build_scheduler(s)
            scheduler.start()
        try:
            yield
        finally:
            if scheduler is not None:
                scheduler.shutdown(wait=False)

    app = FastAPI(
        title="Orbital Conjunctions Dashboard API",
        version=__version__,
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=s.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(health.router, prefix="/api", tags=["health"])
    app.include_router(stats.router, prefix="/api", tags=["stats"])
    app.include_router(satellites.router, prefix="/api", tags=["satellites"])
    app.include_router(conjunctions.router, prefix="/api", tags=["conjunctions"])

    return app


app = create_app()
