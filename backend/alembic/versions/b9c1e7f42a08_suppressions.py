"""add suppressions

Records a user's dismissal so re-analysis stops recreating an equivalent finding
for the same target (feedback loop). One row per (repository, kind, target).

Revision ID: b9c1e7f42a08
Revises: a4d9f2c81e63
Create Date: 2026-07-27

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "b9c1e7f42a08"
down_revision: Union[str, None] = "a4d9f2c81e63"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "suppressions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "repository_id",
            sa.Integer(),
            sa.ForeignKey("repositories.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("kind", sa.String(length=16), nullable=False),
        sa.Column("target", sa.String(length=1024), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.UniqueConstraint(
            "repository_id", "kind", "target", name="uq_suppression_repo_kind_target"
        ),
    )
    op.create_index("ix_suppressions_repository_id", "suppressions", ["repository_id"])


def downgrade() -> None:
    op.drop_index("ix_suppressions_repository_id", table_name="suppressions")
    op.drop_table("suppressions")
