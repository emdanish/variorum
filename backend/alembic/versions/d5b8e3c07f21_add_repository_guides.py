"""add repository_guides

Revision ID: d5b8e3c07f21
Revises: c7d2f1a9b4e0
Create Date: 2026-07-26

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "d5b8e3c07f21"
down_revision: Union[str, None] = "c7d2f1a9b4e0"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "repository_guides",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("repository_id", sa.Integer(), nullable=False),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column(
            "content",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
        ),
        sa.Column("provider", sa.String(length=64), nullable=True),
        sa.Column("model", sa.String(length=128), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False
        ),
        sa.ForeignKeyConstraint(["repository_id"], ["repositories.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("repository_id", name="uq_repository_guides_repository_id"),
    )
    op.create_index(
        op.f("ix_repository_guides_repository_id"),
        "repository_guides",
        ["repository_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_repository_guides_repository_id"), table_name="repository_guides")
    op.drop_table("repository_guides")
