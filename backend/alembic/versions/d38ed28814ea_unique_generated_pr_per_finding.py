"""unique generated_pr per finding

Revision ID: d38ed28814ea
Revises: ee2a65d0ae0f
Create Date: 2026-07-26 16:46:36.819914

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'd38ed28814ea'
down_revision: Union[str, None] = 'ee2a65d0ae0f'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_unique_constraint(
        "uq_generated_prs_drift_finding_id", "generated_prs", ["drift_finding_id"]
    )


def downgrade() -> None:
    op.drop_constraint(
        "uq_generated_prs_drift_finding_id", "generated_prs", type_="unique"
    )
