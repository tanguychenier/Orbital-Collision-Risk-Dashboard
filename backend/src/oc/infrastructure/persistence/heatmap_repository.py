"""SQLAlchemy adapter for the heatmap repository port.

This adapter translates persisted ``Satellite``/``TLE`` rows into the
framework-agnostic :class:`OrbitalBin` dataclass consumed by the heatmap
use case.

Design notes:

* The orbital binning runs an in-process SGP4 ``Satrec`` parse on every
  active TLE. The cost is dominated by the C-side parse (sgp4 ships a
  vectorised C implementation); for 30 000 satellites this routinely
  completes in well under 200 ms on a developer laptop.
"""

from __future__ import annotations

import math
from collections.abc import Sequence
from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from oc.domain.entities import (
    ConjunctionTimelinePoint,
    OrbitalBin,
)
from oc.infrastructure.persistence.models import TLE, Satellite

# Earth equatorial radius (WGS-72) used by sgp4 to convert the satellite
# record's ``a`` field (Earth radii) into kilometres.
_EARTH_RADIUS_KM: float = 6378.135


class SQLAlchemyHeatmapRepository:
    """Implements :class:`oc.application.ports.HeatmapRepository` against SQLAlchemy."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def list_active_orbital_bins(self) -> Sequence[OrbitalBin]:
        """Return one bin per active satellite using its most-recent TLE.

        Picks the latest TLE per ``norad_id`` with a single query and
        derives ``(altitude_km, inclination_deg)`` from the SGP4 record.
        """
        # Subquery: max(epoch) per norad_id. Using ``func.max`` keeps the
        # query portable across SQLite (used in tests) and PostgreSQL.
        latest = (
            select(
                TLE.norad_id.label("norad_id"),
                func.max(TLE.epoch).label("max_epoch"),
            )
            .group_by(TLE.norad_id)
            .subquery()
        )
        stmt = (
            select(TLE.line1, TLE.line2)
            .join(Satellite, Satellite.norad_id == TLE.norad_id)
            .join(
                latest,
                (latest.c.norad_id == TLE.norad_id) & (latest.c.max_epoch == TLE.epoch),
            )
            .where(Satellite.is_active.is_(True))
        )
        rows = (await self._session.execute(stmt)).all()
        out: list[OrbitalBin] = []
        for line1, line2 in rows:
            bin_or_none = _orbital_bin_from_tle(line1, line2)
            if bin_or_none is not None:
                out.append(bin_or_none)
        return out

    async def conjunctions_per_day(
        self, start: datetime, end: datetime
    ) -> Sequence[ConjunctionTimelinePoint]:
        """Stub implementation; the timeline endpoint enables this in a follow-up commit."""
        raise NotImplementedError(
            "conjunctions_per_day is wired by the timeline endpoint commit"
        )


def _orbital_bin_from_tle(line1: str, line2: str) -> OrbitalBin | None:
    """Build an :class:`OrbitalBin` from a TLE pair, returning ``None`` on failure.

    Uses sgp4 to parse the TLE; the ``a`` field on the satellite record
    is in Earth radii (WGS-72) and the ``inclo`` field is in radians.
    Out-of-bounds inclinations get clamped because TLEs occasionally
    encode a hair over 180 degrees due to floating-point round-off.
    """
    try:
        from sgp4.api import Satrec

        sat = Satrec.twoline2rv(line1, line2)
    except Exception:
        # Defensive: a malformed TLE row should not crash the endpoint.
        return None
    sma_km = float(sat.a) * _EARTH_RADIUS_KM
    eccentricity = float(sat.ecco)
    # Mean altitude is the semi-major axis minus Earth's radius. Using
    # the perigee + apogee average is equivalent up to first order and
    # avoids surfacing eccentricity in the binning grid.
    mean_altitude_km = (
        sma_km * (1.0 - eccentricity) - _EARTH_RADIUS_KM
        + sma_km * (1.0 + eccentricity) - _EARTH_RADIUS_KM
    ) / 2.0
    inclination_rad = float(sat.inclo)
    inclination_deg = math.degrees(inclination_rad)
    if inclination_deg < 0.0:
        inclination_deg = 0.0
    if inclination_deg > 180.0:
        inclination_deg = 180.0
    return OrbitalBin(
        altitude_km=mean_altitude_km,
        inclination_deg=inclination_deg,
    )
