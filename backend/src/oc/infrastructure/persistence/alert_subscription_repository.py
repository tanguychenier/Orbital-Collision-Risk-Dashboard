"""SQLAlchemy adapters for the alert subsystem ports.

Implements:

* :class:`SQLAlchemyAlertSubscriptionRepository` -- writes / reads
  against ``alert_subscriptions`` and ``alert_subscription_deliveries``.
* :class:`SQLAlchemyConjunctionAlertSource` -- read-only view over
  ``conjunctions`` filtered by NORAD ids and miss-distance threshold,
  used by :func:`oc.application.use_cases.notify_pending_alerts`.
"""

from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime

from sqlalchemy import or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from oc.domain.entities import AlertSubscription as AlertSubscriptionEntity
from oc.infrastructure.persistence.models import (
    AlertSubscription as AlertSubscriptionRow,
)
from oc.infrastructure.persistence.models import (
    AlertSubscriptionDelivery,
    Conjunction,
)


class SQLAlchemyAlertSubscriptionRepository:
    """Implements the :class:`AlertSubscriptionRepository` port over SQLAlchemy."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, subscription: AlertSubscriptionEntity) -> None:
        """Persist a new subscription row."""
        self._session.add(_to_row(subscription))
        await self._session.flush()

    async def get(self, subscription_id: str) -> AlertSubscriptionEntity | None:
        """Fetch one subscription by id, returning the domain entity."""
        row = await self._session.get(AlertSubscriptionRow, subscription_id)
        return _to_entity(row) if row is not None else None

    async def list_active(self) -> Sequence[AlertSubscriptionEntity]:
        """Return every active subscription as domain entities."""
        stmt = select(AlertSubscriptionRow).where(AlertSubscriptionRow.is_active.is_(True))
        rows = (await self._session.execute(stmt)).scalars().all()
        return [_to_entity(r) for r in rows]

    async def deactivate(self, subscription_id: str) -> None:
        """Mark a subscription as inactive (soft delete)."""
        await self._session.execute(
            update(AlertSubscriptionRow)
            .where(AlertSubscriptionRow.id == subscription_id)
            .values(is_active=False)
        )
        await self._session.flush()

    async def mark_notified(self, subscription_id: str, when: datetime) -> None:
        """Update the ``last_notified_at`` field for ``subscription_id``."""
        await self._session.execute(
            update(AlertSubscriptionRow)
            .where(AlertSubscriptionRow.id == subscription_id)
            .values(last_notified_at=when)
        )
        await self._session.flush()

    async def has_been_notified(self, subscription_id: str, conjunction_id: str) -> bool:
        """Return ``True`` iff this subscription already received this conjunction id."""
        stmt = select(AlertSubscriptionDelivery.id).where(
            AlertSubscriptionDelivery.subscription_id == subscription_id,
            AlertSubscriptionDelivery.conjunction_id == conjunction_id,
        )
        result = await self._session.scalar(stmt)
        return result is not None

    async def record_notified(self, subscription_id: str, conjunction_id: str) -> None:
        """Insert a delivery row for ``(subscription_id, conjunction_id)``."""
        self._session.add(
            AlertSubscriptionDelivery(
                subscription_id=subscription_id,
                conjunction_id=conjunction_id,
            )
        )
        await self._session.flush()


class SQLAlchemyConjunctionAlertSource:
    """Read-only view of upcoming conjunctions, used by the alert loop."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def upcoming_conjunctions_for_satellites(
        self,
        norad_ids: Sequence[int],
        max_distance_km: float,
        until: datetime,
    ) -> Sequence[dict[str, object]]:
        """Return upcoming conjunctions touching ``norad_ids`` below ``max_distance_km``."""
        if not norad_ids:
            return []
        ids = list(norad_ids)
        stmt = (
            select(Conjunction)
            .options(
                selectinload(Conjunction.sat_a),
                selectinload(Conjunction.sat_b),
            )
            .where(
                or_(
                    Conjunction.sat_a_norad_id.in_(ids),
                    Conjunction.sat_b_norad_id.in_(ids),
                ),
                Conjunction.miss_distance_km <= max_distance_km,
                Conjunction.tca <= until,
            )
            .order_by(Conjunction.tca)
        )
        rows = (await self._session.execute(stmt)).scalars().all()
        out: list[dict[str, object]] = []
        for c in rows:
            out.append(
                {
                    "id": c.id,
                    "sat_a_norad_id": c.sat_a_norad_id,
                    "sat_a_name": c.sat_a.name,
                    "sat_b_norad_id": c.sat_b_norad_id,
                    "sat_b_name": c.sat_b.name,
                    "tca": c.tca,
                    "miss_distance_km": float(c.miss_distance_km),
                    "relative_velocity_km_s": float(c.relative_velocity_km_s),
                    "probability": float(c.probability),
                }
            )
        return out


def _to_row(entity: AlertSubscriptionEntity) -> AlertSubscriptionRow:
    """Map a domain entity onto the SQLAlchemy row."""
    return AlertSubscriptionRow(
        id=entity.id,
        email_or_webhook_url=entity.email_or_webhook_url,
        norad_ids=list(entity.norad_ids),
        miss_distance_km_threshold=entity.miss_distance_km_threshold,
        secret_token=entity.secret_token,
        is_active=entity.is_active,
        created_at=entity.created_at,
        last_notified_at=entity.last_notified_at,
    )


def _to_entity(row: AlertSubscriptionRow) -> AlertSubscriptionEntity:
    """Map a SQLAlchemy row to the immutable domain entity."""
    return AlertSubscriptionEntity(
        id=row.id,
        email_or_webhook_url=row.email_or_webhook_url,
        norad_ids=tuple(int(n) for n in row.norad_ids),
        miss_distance_km_threshold=float(row.miss_distance_km_threshold),
        secret_token=row.secret_token,
        is_active=bool(row.is_active),
        created_at=row.created_at,
        last_notified_at=row.last_notified_at,
    )
