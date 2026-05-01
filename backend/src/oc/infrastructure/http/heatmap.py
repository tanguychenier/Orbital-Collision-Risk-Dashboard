"""``/api/heatmap/*`` endpoints.

Two endpoints share this router:

* ``GET /api/heatmap/altitude-inclination`` returns a 2D matrix of
  satellite counts binned by altitude band (50 km wide, 200-2000 km) and
  inclination band (5 deg wide, 0-180 deg).
* ``GET /api/heatmap/conjunctions-timeline?days=N`` returns a daily
  bucketed conjunction count over the past ``N`` days.

Both endpoints delegate to use cases under
:mod:`oc.application.use_cases.compute_heatmap`. The HTTP adapter wires
the SQLAlchemy repository, validates the query parameters, and shapes
the response payload.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from oc.application.use_cases.compute_heatmap import (
    compute_conjunctions_timeline,
    compute_heatmap,
)
from oc.db import get_db_session
from oc.domain.entities import (
    HEATMAP_ALTITUDE_STEP_KM,
    HEATMAP_INCLINATION_STEP_DEG,
)
from oc.infrastructure.persistence.heatmap_repository import (
    SQLAlchemyHeatmapRepository,
)
from oc.interface.schemas import (
    ConjunctionTimelinePoint as ConjunctionTimelinePointSchema,
)
from oc.interface.schemas import (
    HeatmapAltitudeInclinationResponse,
)

# Bound the timeline window to keep the response deterministic and the
# database scan well-bounded. A year of daily buckets is the maximum a
# typical ECharts area chart can render usefully without zoom controls.
_MIN_TIMELINE_DAYS: int = 1
_MAX_TIMELINE_DAYS: int = 365
_DEFAULT_TIMELINE_DAYS: int = 30

router = APIRouter(prefix="/heatmap")


@router.get(
    "/altitude-inclination",
    response_model=HeatmapAltitudeInclinationResponse,
)
async def altitude_inclination(
    session: AsyncSession = Depends(get_db_session),
) -> HeatmapAltitudeInclinationResponse:
    """Return the satellite-count matrix per altitude / inclination band."""
    repository = SQLAlchemyHeatmapRepository(session)
    matrix = await compute_heatmap(repository)
    return HeatmapAltitudeInclinationResponse(
        altitude_bands=list(matrix.altitude_bands),
        inclination_bands=list(matrix.inclination_bands),
        altitude_step_km=HEATMAP_ALTITUDE_STEP_KM,
        inclination_step_deg=HEATMAP_INCLINATION_STEP_DEG,
        counts=[list(row) for row in matrix.counts],
        total_satellites=matrix.total_satellites,
    )


@router.get(
    "/conjunctions-timeline",
    response_model=list[ConjunctionTimelinePointSchema],
)
async def conjunctions_timeline(
    days: int = Query(
        default=_DEFAULT_TIMELINE_DAYS,
        ge=_MIN_TIMELINE_DAYS,
        le=_MAX_TIMELINE_DAYS,
        description="Window length in days (defaults to 30).",
    ),
    session: AsyncSession = Depends(get_db_session),
) -> list[ConjunctionTimelinePointSchema]:
    """Return a per-day count of conjunctions over the past ``days`` days."""
    repository = SQLAlchemyHeatmapRepository(session)
    points = await compute_conjunctions_timeline(repository, days=days)
    return [
        ConjunctionTimelinePointSchema(
            date=point.date,
            miss_lt_1km=point.miss_lt_1km,
            miss_lt_5km=point.miss_lt_5km,
            total=point.total,
        )
        for point in points
    ]
