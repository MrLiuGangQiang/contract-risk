"""add snippet offsets to contract risk

Revision ID: c9d8e7f6a5b4
Revises: a1b2c3d4e5f6
Create Date: 2026-08-29 23:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "c9d8e7f6a5b4"
down_revision: Union[str, Sequence[str], None] = "a1b2c3d4e5f6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """风险点在合同原文中的起止偏移（用于预览定位与局部高亮）。"""
    op.add_column("sys_contract_risk", sa.Column("snippet_start", sa.Integer(), nullable=True))
    op.add_column("sys_contract_risk", sa.Column("snippet_end", sa.Integer(), nullable=True))


def downgrade() -> None:
    op.drop_column("sys_contract_risk", "snippet_end")
    op.drop_column("sys_contract_risk", "snippet_start")
