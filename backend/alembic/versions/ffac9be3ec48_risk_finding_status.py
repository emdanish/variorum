"""risk_finding status

Revision ID: ffac9be3ec48
Revises: 60c01117d50e
Create Date: 2026-07-26 19:28:33.920155

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'ffac9be3ec48'
down_revision: Union[str, None] = '60c01117d50e'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "risk_findings",
        sa.Column("status", sa.String(length=32), nullable=False, server_default="open"),
    )
    op.alter_column("risk_findings", "status", server_default=None)


def downgrade() -> None:
    op.drop_column("risk_findings", "status")
