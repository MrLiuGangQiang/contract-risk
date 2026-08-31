"""风险规则模型（《10-合同风险规则配置设计》第 2 节）。

规则配置由超管维护，后续扫描引擎按 code + keywords 使用。
"""
from datetime import datetime
from sqlalchemy import (
    BigInteger,
    Boolean,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, OperatorMixin, SoftDeleteMixin, TimestampMixin


class RiskRule(TimestampMixin, SoftDeleteMixin, OperatorMixin, Base):
    """合同风险规则表（sys_risk_rule）：一句话规则 + 主键 id。

    极简模型（《10》3.1）：rule_text 是 AI 理解并校验合同的唯一依据；
    category 为开放维度（纯展示分组，可空）；severity 由 AI 判定。
    """

    __tablename__ = "sys_risk_rule"
    __table_args__ = (
        Index("ix_sys_risk_rule_category", "category"),
        Index("ix_sys_risk_rule_enabled", "enabled"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    rule_text: Mapped[str] = mapped_column(Text, nullable=False)
    category: Mapped[str | None] = mapped_column(String(32), nullable=True)
    enabled: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, server_default=text("true")
    )
    sort_order: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default=text("0")
    )


class RiskRuleCustom(TimestampMixin, Base):
    """个人风险规则副本（sys_risk_rule_custom，rule_id 关联全局规则）。"""

    __tablename__ = "sys_risk_rule_custom"
    __table_args__ = (
        UniqueConstraint("user_id", "rule_id", name="uq_sys_risk_rule_custom_user_rule"),
        Index("ix_sys_risk_rule_custom_user_id", "user_id"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("sys_user.id", ondelete="RESTRICT"), nullable=False
    )
    rule_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("sys_risk_rule.id", ondelete="CASCADE"), nullable=False
    )
    rule_text: Mapped[str] = mapped_column(Text, nullable=False)
    category: Mapped[str | None] = mapped_column(String(32), nullable=True)
    enabled: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, server_default=text("true")
    )
    sort_order: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default=text("0")
    )
