"""add decision_entries

Revision ID: f3c8a1e6d924
Revises: e9a1c4d7b350
Create Date: 2026-07-26

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "f3c8a1e6d924"
down_revision: Union[str, None] = "e9a1c4d7b350"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "decision_entries",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("repository_id", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(length=300), nullable=False),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column("sources", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("decided_at", sa.DateTime(timezone=True), nullable=True),
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
    )
    op.create_index(
        op.f("ix_decision_entries_repository_id"),
        "decision_entries",
        ["repository_id"],
        unique=False,
    )
    op.create_index(
        "ix_decision_entries_repo_decided",
        "decision_entries",
        ["repository_id", "decided_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_decision_entries_repo_decided", table_name="decision_entries")
    op.drop_index(op.f("ix_decision_entries_repository_id"), table_name="decision_entries")
    op.drop_table("decision_entries")
