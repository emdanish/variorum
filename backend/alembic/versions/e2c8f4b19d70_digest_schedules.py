"""add digest_schedules

Weekly digest delivery cadence per repository (UTC day-of-week + hour), driven
by the in-process scheduler. One row per repository.

Revision ID: e2c8f4b19d70
Revises: d1e5b7a34f96
Create Date: 2026-07-27

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "e2c8f4b19d70"
down_revision: Union[str, None] = "d1e5b7a34f96"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "digest_schedules",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "repository_id",
            sa.Integer(),
            sa.ForeignKey("repositories.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("day_of_week", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("hour", sa.Integer(), nullable=False, server_default="9"),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("last_sent_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
    )
    op.create_index(
        "ix_digest_schedules_repository_id",
        "digest_schedules",
        ["repository_id"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index("ix_digest_schedules_repository_id", table_name="digest_schedules")
    op.drop_table("digest_schedules")
