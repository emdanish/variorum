"""add decision_entries.embedding

Adds a JSONB embedding column to decision_entries so synthesized decisions are
semantically retrievable in the engineering-memory Q&A (same convention as
knowledge_entries.embedding). Decisions are few per repository, so in-process
cosine over JSONB is sufficient — no pgvector mirror.

Revision ID: c4f9a2e17b83
Revises: b8e4d21a6c37
Create Date: 2026-07-27

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "c4f9a2e17b83"
down_revision: Union[str, None] = "b8e4d21a6c37"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "decision_entries",
        sa.Column("embedding", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("decision_entries", "embedding")
