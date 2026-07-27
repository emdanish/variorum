"""add documents.body and documents.embedding

Store documentation text (truncated) + its embedding so the Q&A can retrieve and
cite the actual doc passages, not just link to the file.

Revision ID: c5e0a9b7d132
Revises: b9c1e7f42a08
Create Date: 2026-07-27

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "c5e0a9b7d132"
down_revision: Union[str, None] = "b9c1e7f42a08"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("documents", sa.Column("body", sa.Text(), nullable=True))
    op.add_column(
        "documents",
        sa.Column("embedding", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("documents", "embedding")
    op.drop_column("documents", "body")
