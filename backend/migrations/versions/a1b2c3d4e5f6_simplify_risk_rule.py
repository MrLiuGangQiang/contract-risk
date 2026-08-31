"""simplify risk rule model

Revision ID: a1b2c3d4e5f6
Revises: f1a2b3c4d5e6
Create Date: 2026-08-29 22:00:00.000000

极简规则模型（《10》3 节）：
- sys_risk_rule 删除 code/name/severity/keywords/description/suggestion（一句话规则 + 主键 id 即可）；
- sys_risk_rule_custom 改为 rule_id 外键关联全局规则；
- sys_contract_risk 新增 rule_id（快照引用），rule_code 置为可空（历史数据保留）。
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "a1b2c3d4e5f6"
down_revision: Union[str, Sequence[str], None] = "f1a2b3c4d5e6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ---------- sys_risk_rule 瘦身 ----------
    op.drop_index("uq_sys_risk_rule_code", table_name="sys_risk_rule")
    op.drop_column("sys_risk_rule", "code")
    op.drop_column("sys_risk_rule", "name")
    op.drop_column("sys_risk_rule", "severity")
    op.drop_column("sys_risk_rule", "keywords")
    op.drop_column("sys_risk_rule", "description")
    op.drop_column("sys_risk_rule", "suggestion")

    # ---------- sys_risk_rule_custom：rule_id 外键关联 ----------
    op.drop_constraint(
        "uq_sys_risk_rule_custom_user_code", "sys_risk_rule_custom", type_="unique"
    )
    op.add_column(
        "sys_risk_rule_custom",
        sa.Column("rule_id", sa.BigInteger(), nullable=True),
    )
    op.create_foreign_key(
        "fk_sys_risk_rule_custom_rule_id",
        "sys_risk_rule_custom",
        "sys_risk_rule",
        ["rule_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.create_unique_constraint(
        "uq_sys_risk_rule_custom_user_rule",
        "sys_risk_rule_custom",
        ["user_id", "rule_id"],
    )
    op.drop_column("sys_risk_rule_custom", "code")
    op.drop_column("sys_risk_rule_custom", "name")
    op.drop_column("sys_risk_rule_custom", "severity")
    op.drop_column("sys_risk_rule_custom", "keywords")
    op.drop_column("sys_risk_rule_custom", "description")
    op.drop_column("sys_risk_rule_custom", "suggestion")

    # ---------- sys_contract_risk：rule_id 引用 + rule_code 可空 ----------
    op.add_column(
        "sys_contract_risk",
        sa.Column("rule_id", sa.BigInteger(), nullable=True),
    )
    op.alter_column("sys_contract_risk", "rule_code", existing_type=sa.String(64), nullable=True)


def downgrade() -> None:
    """Downgrade schema."""
    op.alter_column("sys_contract_risk", "rule_code", existing_type=sa.String(64), nullable=False)
    op.drop_column("sys_contract_risk", "rule_id")

    op.add_column("sys_risk_rule_custom", sa.Column("suggestion", sa.Text(), nullable=False, server_default=""))
    op.add_column("sys_risk_rule_custom", sa.Column("description", sa.Text(), nullable=False, server_default=""))
    op.add_column("sys_risk_rule_custom", sa.Column("keywords", sa.JSON(), nullable=False, server_default="[]"))
    op.add_column("sys_risk_rule_custom", sa.Column("severity", sa.String(16), nullable=False, server_default="medium"))
    op.add_column("sys_risk_rule_custom", sa.Column("name", sa.String(128), nullable=False, server_default=""))
    op.add_column("sys_risk_rule_custom", sa.Column("code", sa.String(64), nullable=False, server_default=""))
    op.drop_constraint("uq_sys_risk_rule_custom_user_rule", "sys_risk_rule_custom", type_="unique")
    op.drop_constraint("fk_sys_risk_rule_custom_rule_id", "sys_risk_rule_custom", type_="foreignkey")
    op.drop_column("sys_risk_rule_custom", "rule_id")

    op.add_column("sys_risk_rule", sa.Column("suggestion", sa.Text(), nullable=False, server_default=""))
    op.add_column("sys_risk_rule", sa.Column("description", sa.Text(), nullable=False, server_default=""))
    op.add_column("sys_risk_rule", sa.Column("keywords", sa.JSON(), nullable=False, server_default="[]"))
    op.add_column("sys_risk_rule", sa.Column("severity", sa.String(16), nullable=False, server_default="medium"))
    op.add_column("sys_risk_rule", sa.Column("name", sa.String(128), nullable=False, server_default=""))
    op.add_column("sys_risk_rule", sa.Column("code", sa.String(64), nullable=False, server_default=""))
