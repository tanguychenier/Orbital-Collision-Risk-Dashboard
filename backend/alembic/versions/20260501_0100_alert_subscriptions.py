"""Add alert subscriptions and delivery-tracking tables.

Revision ID: 20260501_0100
Revises: 20260501_0000
Create Date: 2026-05-01 01:00:00

"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260501_0100"
down_revision: str | None = "20260501_0000"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create the ``alert_subscriptions`` and delivery-tracking tables."""
    op.create_table(
        "alert_subscriptions",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("email_or_webhook_url", sa.String(length=512), nullable=False),
        sa.Column("norad_ids", sa.JSON(), nullable=False),
        sa.Column("miss_distance_km_threshold", sa.Float(), nullable=False),
        sa.Column("secret_token", sa.String(length=64), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_notified_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index(
        "ix_alert_subscriptions_is_active",
        "alert_subscriptions",
        ["is_active"],
    )

    op.create_table(
        "alert_subscription_deliveries",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column(
            "subscription_id",
            sa.String(length=36),
            sa.ForeignKey("alert_subscriptions.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("conjunction_id", sa.String(length=36), nullable=False),
        sa.Column("notified_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint(
            "subscription_id",
            "conjunction_id",
            name="uq_alert_deliveries_pair",
        ),
    )
    op.create_index(
        "ix_alert_deliveries_subscription",
        "alert_subscription_deliveries",
        ["subscription_id"],
    )


def downgrade() -> None:
    """Drop alert tables in reverse dependency order."""
    op.drop_index(
        "ix_alert_deliveries_subscription",
        table_name="alert_subscription_deliveries",
    )
    op.drop_table("alert_subscription_deliveries")
    op.drop_index(
        "ix_alert_subscriptions_is_active",
        table_name="alert_subscriptions",
    )
    op.drop_table("alert_subscriptions")
