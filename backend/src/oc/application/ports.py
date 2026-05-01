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
    AlertSubscription,
    ConjunctionEvent,
    ConjunctionTimelinePoint,
    OrbitalBin,
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
class SatelliteRepository(Protocol):
    """Persistence boundary for satellite lookups exposed by the public API."""

    async def find_by_identifier(
        self, identifier: str
    ) -> tuple[SatelliteRecord, TLERecord | None] | None:
        """Resolve a NORAD id (digits) or exact name to a satellite + last TLE."""

    async def search(self, query: str | None, limit: int) -> Sequence[SatelliteRecord]:
        """Return up to ``limit`` satellites matching ``query`` (fuzzy on name, exact on id)."""


@runtime_checkable
class ConjunctionRepository(Protocol):
    """Persistence boundary for the ``conjunctions`` table."""

    async def replace_all(self, events: Sequence[ConjunctionEvent]) -> None:
        """Atomically replace the table contents with ``events``."""


@runtime_checkable
class AlertSubscriptionRepository(Protocol):
    """Persistence boundary for the ``alert_subscriptions`` table."""

    async def add(self, subscription: AlertSubscription) -> None:
        """Persist a brand-new subscription."""

    async def get(self, subscription_id: str) -> AlertSubscription | None:
        """Fetch one subscription by its UUID, or ``None`` if not found."""

    async def list_active(self) -> Sequence[AlertSubscription]:
        """Return every subscription whose ``is_active`` flag is ``True``."""

    async def deactivate(self, subscription_id: str) -> None:
        """Soft-delete a subscription by setting ``is_active=False``."""

    async def mark_notified(self, subscription_id: str, when: datetime) -> None:
        """Set the ``last_notified_at`` timestamp for ``subscription_id``."""

    async def has_been_notified(self, subscription_id: str, conjunction_id: str) -> bool:
        """Return ``True`` if ``conjunction_id`` was already delivered to this subscription."""

    async def record_notified(self, subscription_id: str, conjunction_id: str) -> None:
        """Record that ``conjunction_id`` was delivered to this subscription."""


@runtime_checkable
class AlertNotifier(Protocol):
    """Outbound port for delivering an alert payload (email or webhook)."""

    async def notify(
        self,
        target: str,
        subject: str,
        message: str,
        payload: dict[str, object],
    ) -> bool:
        """Deliver ``payload`` to ``target``. Return ``True`` if delivery succeeded."""


@runtime_checkable
class ConjunctionAlertSource(Protocol):
    """Read-only port exposing conjunctions to the alert notification loop."""

    async def upcoming_conjunctions_for_satellites(
        self,
        norad_ids: Sequence[int],
        max_distance_km: float,
        until: datetime,
    ) -> Sequence[dict[str, object]]:
        """Return upcoming conjunctions touching ``norad_ids`` below the threshold.

        Each row is a plain dict with the keys:

        ``id``, ``sat_a_norad_id``, ``sat_a_name``, ``sat_b_norad_id``,
        ``sat_b_name``, ``tca``, ``miss_distance_km``,
        ``relative_velocity_km_s`` and ``probability``. Returning a dict
        keeps the application layer independent from the SQLAlchemy row
        type while still being trivial to fake.
        """


@runtime_checkable
class HeatmapRepository(Protocol):
    """Persistence boundary for the orbital congestion heatmap.

    Adapters are responsible for translating the persisted TLE pairs into
    a stream of :class:`OrbitalBin` instances and aggregating the
    conjunctions table by day. Keeping the bin extraction on the adapter
    side lets the SQL adapter use ``GROUP BY`` for the timeline aggregation
    and a single tight loop in Python for the binning, both of which keep
    the endpoint well under the 200 ms budget at 30 000 satellites.
    """

    async def list_active_orbital_bins(self) -> Sequence[OrbitalBin]:
        """Return one :class:`OrbitalBin` per active tracked satellite.

        Implementations should consume the most-recent TLE per active
        satellite and propagate it to derive ``altitude_km`` and
        ``inclination_deg``. The order of the returned sequence is not
        significant.
        """

    async def conjunctions_per_day(
        self, start: datetime, end: datetime
    ) -> Sequence[ConjunctionTimelinePoint]:
        """Aggregate the ``conjunctions`` table by calendar day in ``[start, end]``.

        Implementations must return one :class:`ConjunctionTimelinePoint`
        per day in the inclusive range, even when no conjunction
        materialised on that day (counts then default to ``0``).
        """


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
