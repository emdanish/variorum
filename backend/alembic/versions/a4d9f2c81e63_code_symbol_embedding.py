"""add code_symbols.embedding

JSONB embedding on code symbols so the engineering-memory Q&A can retrieve and
cite the actual code (functions/classes), not only the history written about it.

Revision ID: a4d9f2c81e63
Revises: f7a3c9e51d24
Create Date: 2026-07-27

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "a4d9f2c81e63"
down_revision: Union[str, None] = "f7a3c9e51d24"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "code_symbols",
        sa.Column("embedding", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("code_symbols", "embedding")
