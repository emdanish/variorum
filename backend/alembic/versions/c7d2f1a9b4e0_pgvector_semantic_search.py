"""pgvector semantic search (optional acceleration, guarded)

Adds an indexed pgvector column that mirrors the JSONB ``embedding`` column, so
semantic search scales to large repositories. This migration is *guarded*: if
the ``vector`` extension is not available on the server it does nothing, and the
application transparently keeps using the JSONB + in-process cosine path. That
means ``alembic upgrade head`` never fails on a server without pgvector.

A trigger keeps ``embedding_vec`` in sync with ``embedding`` on every write, so
no application code has to change.

Revision ID: c7d2f1a9b4e0
Revises: ffac9be3ec48
Create Date: 2026-07-26

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "c7d2f1a9b4e0"
down_revision: Union[str, None] = "ffac9be3ec48"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


_SYNC_FUNCTION = """
CREATE OR REPLACE FUNCTION variorum_sync_embedding_vec() RETURNS trigger AS $$
BEGIN
    IF NEW.embedding IS NULL THEN
        NEW.embedding_vec := NULL;
    ELSE
        NEW.embedding_vec := replace(NEW.embedding::text, ' ', '')::vector;
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;
"""


def _vector_available(bind: sa.engine.Connection) -> bool:
    return bool(
        bind.execute(
            sa.text("SELECT 1 FROM pg_available_extensions WHERE name = 'vector'")
        ).scalar()
    )


def upgrade() -> None:
    bind = op.get_bind()
    if not _vector_available(bind):
        # pgvector is not installed on this server — keep the JSONB path. This is
        # the case on the default local/dev setup; nothing else to do.
        return

    op.execute("CREATE EXTENSION IF NOT EXISTS vector")
    op.execute("ALTER TABLE knowledge_entries ADD COLUMN IF NOT EXISTS embedding_vec vector(768)")
    op.execute(_SYNC_FUNCTION)
    op.execute("DROP TRIGGER IF EXISTS trg_sync_embedding_vec ON knowledge_entries")
    op.execute(
        "CREATE TRIGGER trg_sync_embedding_vec "
        "BEFORE INSERT OR UPDATE OF embedding ON knowledge_entries "
        "FOR EACH ROW EXECUTE FUNCTION variorum_sync_embedding_vec()"
    )
    # Backfill any rows that already have a JSONB embedding.
    op.execute(
        "UPDATE knowledge_entries "
        "SET embedding_vec = replace(embedding::text, ' ', '')::vector "
        "WHERE embedding IS NOT NULL AND embedding_vec IS NULL"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_knowledge_embedding_vec "
        "ON knowledge_entries USING hnsw (embedding_vec vector_cosine_ops)"
    )


def downgrade() -> None:
    bind = op.get_bind()
    if not _vector_available(bind):
        return
    op.execute("DROP INDEX IF EXISTS ix_knowledge_embedding_vec")
    op.execute("DROP TRIGGER IF EXISTS trg_sync_embedding_vec ON knowledge_entries")
    op.execute("DROP FUNCTION IF EXISTS variorum_sync_embedding_vec()")
    op.execute("ALTER TABLE knowledge_entries DROP COLUMN IF EXISTS embedding_vec")
