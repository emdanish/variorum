"""generated_pr risk_finding_id

Revision ID: 60c01117d50e
Revises: 207ea974cf8d
Create Date: 2026-07-26 17:53:37.143294

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '60c01117d50e'
down_revision: Union[str, None] = '207ea974cf8d'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('generated_prs', sa.Column('risk_finding_id', sa.Integer(), nullable=True))
    op.create_unique_constraint(
        'uq_generated_prs_risk_finding_id', 'generated_prs', ['risk_finding_id']
    )
    op.create_foreign_key(
        'fk_generated_prs_risk_finding_id', 'generated_prs', 'risk_findings',
        ['risk_finding_id'], ['id'], ondelete='SET NULL',
    )


def downgrade() -> None:
    op.drop_constraint('fk_generated_prs_risk_finding_id', 'generated_prs', type_='foreignkey')
    op.drop_constraint('uq_generated_prs_risk_finding_id', 'generated_prs', type_='unique')
    op.drop_column('generated_prs', 'risk_finding_id')
