"""add repositories.pr_comments_enabled

Opt-in flag controlling whether Variorum auto-posts a PR impact-briefing comment
on pull_request webhooks. Defaults to false (server-side default backfills
existing rows) — outward-facing posting is never on without the owner's consent.

Revision ID: d1e5b7a34f96
Revises: c4f9a2e17b83
Create Date: 2026-07-27

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "d1e5b7a34f96"
down_revision: Union[str, None] = "c4f9a2e17b83"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "repositories",
        sa.Column(
            "pr_comments_enabled",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
    )


def downgrade() -> None:
    op.drop_column("repositories", "pr_comments_enabled")
