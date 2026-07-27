"""add global_usage

Revision ID: e1f4a7c2b9d3
Revises: d8b3c6a1f9e2
Create Date: 2026-07-27

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "e1f4a7c2b9d3"
down_revision: Union[str, None] = "d8b3c6a1f9e2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "global_usage",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("scope", sa.String(length=32), nullable=False),
        sa.Column("period_start", sa.DateTime(timezone=True), nullable=False),
        sa.Column("used", sa.Integer(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("scope"),
    )


def downgrade() -> None:
    op.drop_table("global_usage")
