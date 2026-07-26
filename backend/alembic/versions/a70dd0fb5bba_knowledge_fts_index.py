"""knowledge fts index

Revision ID: a70dd0fb5bba
Revises: 00a46f90c915
Create Date: 2026-07-26 17:05:46.686284

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'a70dd0fb5bba'
down_revision: Union[str, None] = '00a46f90c915'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


_FTS_EXPR = "to_tsvector('english', coalesce(title, '') || ' ' || coalesce(body, ''))"


def upgrade() -> None:
    op.execute(
        f"CREATE INDEX ix_knowledge_entries_fts ON knowledge_entries USING gin ({_FTS_EXPR})"
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_knowledge_entries_fts")
