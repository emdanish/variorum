"""add metric_snapshots and alerts

Snapshot time-series (health, coverage, ownership, hotspots, findings) powering
trend charts (4D) and alert diffs (4B), plus an alerts table for the in-app
notification center.

Revision ID: f7a3c9e51d24
Revises: e2c8f4b19d70
Create Date: 2026-07-27

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "f7a3c9e51d24"
down_revision: Union[str, None] = "e2c8f4b19d70"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "metric_snapshots",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "repository_id",
            sa.Integer(),
            sa.ForeignKey("repositories.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("captured_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("health_score", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("doc_coverage_pct", sa.Float(), nullable=False, server_default="0"),
        sa.Column("single_owner_modules", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("module_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("critical_hotspots", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("high_hotspots", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("drift_open", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("risk_open", sa.Integer(), nullable=False, server_default="0"),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
    )
    op.create_index(
        "ix_metric_snapshots_repository_id", "metric_snapshots", ["repository_id"]
    )
    op.create_index(
        "ix_metric_snapshots_repo_captured",
        "metric_snapshots",
        ["repository_id", "captured_at"],
    )

    op.create_table(
        "alerts",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "repository_id",
            sa.Integer(),
            sa.ForeignKey("repositories.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("kind", sa.String(length=48), nullable=False),
        sa.Column("severity", sa.String(length=16), nullable=False, server_default="warning"),
        sa.Column("title", sa.String(length=300), nullable=False),
        sa.Column("detail", sa.Text(), nullable=False, server_default=""),
        sa.Column("acknowledged_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
    )
    op.create_index("ix_alerts_repository_id", "alerts", ["repository_id"])
    op.create_index("ix_alerts_repo_ack", "alerts", ["repository_id", "acknowledged_at"])


def downgrade() -> None:
    op.drop_index("ix_alerts_repo_ack", table_name="alerts")
    op.drop_index("ix_alerts_repository_id", table_name="alerts")
    op.drop_table("alerts")
    op.drop_index("ix_metric_snapshots_repo_captured", table_name="metric_snapshots")
    op.drop_index("ix_metric_snapshots_repository_id", table_name="metric_snapshots")
    op.drop_table("metric_snapshots")
