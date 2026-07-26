"""add file_changes

Revision ID: e9a1c4d7b350
Revises: d5b8e3c07f21
Create Date: 2026-07-26

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "e9a1c4d7b350"
down_revision: Union[str, None] = "d5b8e3c07f21"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "file_changes",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("repository_id", sa.Integer(), nullable=False),
        sa.Column("commit_sha", sa.String(length=64), nullable=False),
        sa.Column("path", sa.String(length=1024), nullable=False),
        sa.Column("author", sa.String(length=255), nullable=True),
        sa.Column("additions", sa.Integer(), nullable=False),
        sa.Column("deletions", sa.Integer(), nullable=False),
        sa.Column("is_fix", sa.Boolean(), nullable=False),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False
        ),
        sa.ForeignKeyConstraint(["repository_id"], ["repositories.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("repository_id", "commit_sha", "path", name="uq_file_change"),
    )
    op.create_index(
        op.f("ix_file_changes_repository_id"), "file_changes", ["repository_id"], unique=False
    )
    op.create_index(
        "ix_file_changes_repo_path", "file_changes", ["repository_id", "path"], unique=False
    )


def downgrade() -> None:
    op.drop_index("ix_file_changes_repo_path", table_name="file_changes")
    op.drop_index(op.f("ix_file_changes_repository_id"), table_name="file_changes")
    op.drop_table("file_changes")
