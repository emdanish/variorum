"""add users.github_login

Revision ID: f2a9d5c8b1e4
Revises: e1f4a7c2b9d3
Create Date: 2026-07-27

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "f2a9d5c8b1e4"
down_revision: Union[str, None] = "e1f4a7c2b9d3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("users", sa.Column("github_login", sa.String(length=255), nullable=True))
    op.create_index(op.f("ix_users_github_login"), "users", ["github_login"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_users_github_login"), table_name="users")
    op.drop_column("users", "github_login")
