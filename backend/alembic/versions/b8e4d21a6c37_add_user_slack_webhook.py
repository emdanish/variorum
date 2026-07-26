"""add user slack_webhook_url

Revision ID: b8e4d21a6c37
Revises: a2f7b1c93d05
Create Date: 2026-07-27

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "b8e4d21a6c37"
down_revision: Union[str, None] = "a2f7b1c93d05"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("users", sa.Column("slack_webhook_url", sa.String(length=512), nullable=True))


def downgrade() -> None:
    op.drop_column("users", "slack_webhook_url")
