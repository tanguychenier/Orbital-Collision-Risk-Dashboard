"""Initial schema: satellites, tles, conjunctions.

Revision ID: 20260501_0000
Revises:
Create Date: 2026-05-01 00:00:00

"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260501_0000"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create all tables."""
    op.create_table(
        "satellites",
        sa.Column("norad_id", sa.Integer(), primary_key=True, autoincrement=False),
        sa.Column("name", sa.String(length=64), nullable=False),
        sa.Column("country", sa.String(length=16), nullable=True),
        sa.Column("object_type", sa.String(length=16), nullable=True),
        sa.Column("launch_date", sa.Date(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_satellites_name", "satellites", ["name"])

    op.create_table(
        "tles",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column(
            "norad_id",
            sa.Integer(),
            sa.ForeignKey("satellites.norad_id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("epoch", sa.DateTime(timezone=True), nullable=False),
        sa.Column("line1", sa.String(length=120), nullable=False),
        sa.Column("line2", sa.String(length=120), nullable=False),
        sa.Column("fetched_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("norad_id", "epoch", name="uq_tles_norad_epoch"),
    )
    op.create_index("ix_tles_norad_id", "tles", ["norad_id"])
    op.create_index("ix_tles_epoch", "tles", ["epoch"])

    op.create_table(
        "conjunctions",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column(
            "sat_a_norad_id",
            sa.Integer(),
            sa.ForeignKey("satellites.norad_id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "sat_b_norad_id",
            sa.Integer(),
            sa.ForeignKey("satellites.norad_id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "tle_a_id",
            sa.Integer(),
            sa.ForeignKey("tles.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "tle_b_id",
            sa.Integer(),
            sa.ForeignKey("tles.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("tca", sa.DateTime(timezone=True), nullable=False),
        sa.Column("miss_distance_km", sa.Float(), nullable=False),
        sa.Column("relative_velocity_km_s", sa.Float(), nullable=False),
        sa.Column("probability", sa.Float(), nullable=False),
        sa.Column("computed_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_conjunctions_sat_a_norad_id", "conjunctions", ["sat_a_norad_id"])
    op.create_index("ix_conjunctions_sat_b_norad_id", "conjunctions", ["sat_b_norad_id"])
    op.create_index("ix_conjunctions_tca", "conjunctions", ["tca"])
    op.create_index("ix_conjunctions_miss", "conjunctions", ["miss_distance_km"])


def downgrade() -> None:
    """Drop all tables."""
    op.drop_index("ix_conjunctions_miss", table_name="conjunctions")
    op.drop_index("ix_conjunctions_tca", table_name="conjunctions")
    op.drop_index("ix_conjunctions_sat_b_norad_id", table_name="conjunctions")
    op.drop_index("ix_conjunctions_sat_a_norad_id", table_name="conjunctions")
    op.drop_table("conjunctions")
    op.drop_index("ix_tles_epoch", table_name="tles")
    op.drop_index("ix_tles_norad_id", table_name="tles")
    op.drop_table("tles")
    op.drop_index("ix_satellites_name", table_name="satellites")
    op.drop_table("satellites")
