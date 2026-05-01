"""``/api/heatmap/*`` endpoints.

* ``GET /api/heatmap/altitude-inclination`` returns a 2D matrix of
  satellite counts binned by altitude band (50 km wide, 200-2000 km) and
  inclination band (5 deg wide, 0-180 deg).

The HTTP adapter delegates the aggregation to the application-layer use
case under :mod:`oc.application.use_cases.compute_heatmap` and shapes
the response payload here.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from oc.application.use_cases.compute_heatmap import compute_heatmap
from oc.db import get_db_session
from oc.domain.entities import (
    HEATMAP_ALTITUDE_STEP_KM,
    HEATMAP_INCLINATION_STEP_DEG,
)
from oc.infrastructure.persistence.heatmap_repository import (
    SQLAlchemyHeatmapRepository,
)
from oc.interface.schemas import HeatmapAltitudeInclinationResponse

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
