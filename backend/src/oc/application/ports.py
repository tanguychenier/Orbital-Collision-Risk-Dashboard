"""Ports (Protocol classes) used by the application layer.

A *port* is the abstract contract a use case depends on. Each concrete
adapter under :mod:`oc.infrastructure` must satisfy a port declared here.
This isolates the application layer from third-party drivers and makes
the use cases trivially unit-testable with in-memory fakes.
"""

from __future__ import annotations

from collections.abc import Callable, Iterable, Sequence
from datetime import datetime
from typing import Protocol, runtime_checkable

from oc.domain.entities import (
    ConjunctionEvent,
    ParsedTLE,
    SatelliteRecord,
    TLERecord,
)
from oc.domain.value_objects import Ephemeris, OrbitalElements


@runtime_checkable
class Clock(Protocol):
    """Source of the current UTC time. Inject a fake to make tests deterministic."""

    def now(self) -> datetime:
        """Return the current time as a timezone-aware UTC ``datetime``."""


@runtime_checkable
class TLESource(Protocol):
    """Inbound source of TLE text (CelesTrak, Space-Track, a local fixture, ...)."""

    async def fetch(self, url: str) -> str:
        """Fetch the raw TLE text body from ``url``."""


@runtime_checkable
class TLERepository(Protocol):
    """Persistence boundary for satellites and TLE records."""

    async def upsert_parsed_tles(self, parsed: Iterable[ParsedTLE]) -> tuple[int, int]:
        """Persist parsed TLEs idempotently. Returns ``(satellites_added, tles_added)``."""

    async def latest_tle_per_active_satellite(self) -> Sequence[tuple[SatelliteRecord, TLERecord]]:
        """Return the most recent TLE for every active satellite."""

    async def find_latest_tle_id(self, norad_id: int) -> int | None:
        """Return the database id of the most recent TLE for ``norad_id``, or ``None``."""


@runtime_checkable
class ConjunctionRepository(Protocol):
    """Persistence boundary for the ``conjunctions`` table."""

    async def replace_all(self, events: Sequence[ConjunctionEvent]) -> None:
        """Atomically replace the table contents with ``events``."""


@runtime_checkable
class Propagator(Protocol):
    """Numerical orbit propagator (typically an SGP4 wrapper)."""

    def build_state(self, line1: str, line2: str) -> object:
        """Compile a TLE pair into an opaque propagator state.

        The returned object is passed back to :meth:`propagate` and
        :meth:`orbital_elements` and is treated as opaque by the
        application layer.
        """

    def propagate(self, state: object, times: Sequence[datetime]) -> Ephemeris:
        """Propagate ``state`` to each timestamp in ``times``."""

    def orbital_elements(self, state: object) -> OrbitalElements:
        """Return gross orbital geometry of ``state``."""


@runtime_checkable
class BoundedScalarMinimizer(Protocol):
    """Bracketed minimizer used to refine a TCA on a sub-second grid."""

    def minimize(
        self,
        objective: Callable[[float], float],
        lower: float,
        upper: float,
        tolerance: float,
    ) -> float:
        """Return the ``x`` in ``[lower, upper]`` that minimises ``objective``."""
