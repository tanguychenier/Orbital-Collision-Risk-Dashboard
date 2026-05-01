"""FastAPI application factory (composition root).

This is the only place where the inbound HTTP adapter is connected to
the outbound adapters (database, scheduler). The function
:func:`create_app` instantiates the FastAPI app, wires routers, and -- if
the scheduler is enabled -- boots the APScheduler instance.
"""

from __future__ import annotations

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Any

import structlog
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from oc import __version__
from oc.config import Settings, get_settings
from oc.db import init_models
from oc.infrastructure.http.api import build_api_router


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

    Returns:
        A fully wired :class:`fastapi.FastAPI` instance ready to serve.
    """
    configure_logging()
    s = settings or get_settings()

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        await init_models()
        scheduler: Any | None = None
        if s.enable_scheduler:
            from oc.infrastructure.scheduler import build_scheduler

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
    app.include_router(build_api_router())
    return app


app = create_app()
