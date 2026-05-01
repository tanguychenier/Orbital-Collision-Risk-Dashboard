"""SQLAlchemy ORM models.

These are *adapter-side* objects: they translate between rows in
PostgreSQL/SQLite and the entities defined in :mod:`oc.domain.entities`.
The application layer never imports them directly; instead it goes
through repository ports.
"""

from __future__ import annotations

from datetime import UTC, date, datetime
from typing import Any

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from oc.db import Base


def _utcnow() -> datetime:
    """Return a timezone-aware UTC ``datetime``."""
    return datetime.now(UTC)


class Satellite(Base):
    """A tracked space object identified by its NORAD catalog id."""

    __tablename__ = "satellites"

    norad_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=False)
    name: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    country: Mapped[str | None] = mapped_column(String(16), nullable=True)
    object_type: Mapped[str | None] = mapped_column(String(16), nullable=True)
    launch_date: Mapped[date | None] = mapped_column(nullable=True)
    is_active: Mapped[bool] = mapped_column(default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, onupdate=_utcnow, nullable=False
    )

    tles: Mapped[list[TLE]] = relationship(
        back_populates="satellite",
        cascade="all, delete-orphan",
        order_by="TLE.epoch.desc()",
    )

    def to_summary(self) -> dict[str, Any]:
        """Render a compact dict matching the API contract for nested usage."""
        return {"norad_id": self.norad_id, "name": self.name}


class TLE(Base):
    """A Two-Line Element record. The ``(norad_id, epoch)`` pair is unique."""

    __tablename__ = "tles"
    __table_args__ = (
        UniqueConstraint("norad_id", "epoch", name="uq_tles_norad_epoch"),
        Index("ix_tles_epoch", "epoch"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    norad_id: Mapped[int] = mapped_column(
        ForeignKey("satellites.norad_id", ondelete="CASCADE"), nullable=False, index=True
    )
    epoch: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    line1: Mapped[str] = mapped_column(String(120), nullable=False)
    line2: Mapped[str] = mapped_column(String(120), nullable=False)
    fetched_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, nullable=False
    )

    satellite: Mapped[Satellite] = relationship(back_populates="tles")


class Conjunction(Base):
    """A predicted close approach between two satellites."""

    __tablename__ = "conjunctions"
    __table_args__ = (
        Index("ix_conjunctions_tca", "tca"),
        Index("ix_conjunctions_miss", "miss_distance_km"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    sat_a_norad_id: Mapped[int] = mapped_column(
        ForeignKey("satellites.norad_id", ondelete="CASCADE"), nullable=False, index=True
    )
    sat_b_norad_id: Mapped[int] = mapped_column(
        ForeignKey("satellites.norad_id", ondelete="CASCADE"), nullable=False, index=True
    )
    tle_a_id: Mapped[int] = mapped_column(ForeignKey("tles.id", ondelete="CASCADE"), nullable=False)
    tle_b_id: Mapped[int] = mapped_column(ForeignKey("tles.id", ondelete="CASCADE"), nullable=False)
    tca: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    miss_distance_km: Mapped[float] = mapped_column(Float, nullable=False)
    relative_velocity_km_s: Mapped[float] = mapped_column(Float, nullable=False)
    probability: Mapped[float] = mapped_column(Float, nullable=False)
    computed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, nullable=False
    )

    sat_a: Mapped[Satellite] = relationship(foreign_keys=[sat_a_norad_id])
    sat_b: Mapped[Satellite] = relationship(foreign_keys=[sat_b_norad_id])
    tle_a: Mapped[TLE] = relationship(foreign_keys=[tle_a_id])
    tle_b: Mapped[TLE] = relationship(foreign_keys=[tle_b_id])


class AlertSubscription(Base):
    """A standing alert subscription for one or more satellites.

    The subsystem is stateless: ``secret_token`` is the only credential
    and is required to inspect or unsubscribe. ``norad_ids`` is stored
    as a JSON array of integers so the row is portable across SQLite
    and PostgreSQL without bespoke array types.
    """

    __tablename__ = "alert_subscriptions"
    __table_args__ = (Index("ix_alert_subscriptions_is_active", "is_active"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    email_or_webhook_url: Mapped[str] = mapped_column(String(512), nullable=False)
    norad_ids: Mapped[list[int]] = mapped_column(JSON, nullable=False)
    miss_distance_km_threshold: Mapped[float] = mapped_column(Float, nullable=False)
    secret_token: Mapped[str] = mapped_column(String(64), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, nullable=False
    )
    last_notified_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )


class AlertSubscriptionDelivery(Base):
    """Tracks which conjunction ids have already been delivered for a subscription.

    The pair ``(subscription_id, conjunction_id)`` is unique so the
    notification loop is safely idempotent and can be rerun without
    re-sending the same alert.
    """

    __tablename__ = "alert_subscription_deliveries"
    __table_args__ = (
        UniqueConstraint(
            "subscription_id",
            "conjunction_id",
            name="uq_alert_deliveries_pair",
        ),
        Index("ix_alert_deliveries_subscription", "subscription_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    subscription_id: Mapped[str] = mapped_column(
        ForeignKey("alert_subscriptions.id", ondelete="CASCADE"), nullable=False
    )
    conjunction_id: Mapped[str] = mapped_column(String(36), nullable=False)
    notified_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, nullable=False
    )
