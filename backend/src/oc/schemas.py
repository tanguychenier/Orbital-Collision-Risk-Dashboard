"""Backwards-compatibility shim.

The Pydantic schemas now live in :mod:`oc.interface.schemas`.
"""

from __future__ import annotations

from oc.interface.schemas import (
    ConjunctionDetail,
    ConjunctionListItem,
    HealthResponse,
    SatelliteDetail,
    SatelliteSummary,
    StatsResponse,
)

__all__ = [
    "ConjunctionDetail",
    "ConjunctionListItem",
    "HealthResponse",
    "SatelliteDetail",
    "SatelliteSummary",
    "StatsResponse",
]
