"""add rule_text to risk rules

Revision ID: f1a2b3c4d5e6
Revises: eed395b7bf44
Create Date: 2026-08-29 09:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "f1a2b3c4d5e6"
down_revision: Union[str, Sequence[str], None] = "eed395b7bf44"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """新增一句话规则字段（向后兼容，缺省回填 name）。"""
    op.add_column(
        "sys_risk_rule",
        sa.Column("rule_text", sa.Text(), nullable=False, server_default=""),
    )
    op.add_column(
        "sys_risk_rule_custom",
        sa.Column("rule_text", sa.Text(), nullable=False, server_default=""),
    )
    # 回填：一句话规则缺省用现有 name（保证已有数据不丢语义）
    op.execute("UPDATE sys_risk_rule SET rule_text = name WHERE rule_text = ''")
    op.execute("UPDATE sys_risk_rule_custom SET rule_text = name WHERE rule_text = ''")


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column("sys_risk_rule_custom", "rule_text")
    op.drop_column("sys_risk_rule", "rule_text")
