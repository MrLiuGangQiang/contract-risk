"""合同与风险结果模型（《11-合同风险识别核心功能设计》第 3 节）。

合同文本与风险结果按用户隔离；风险结果保存规则快照，避免规则变更影响历史结果。
"""
from datetime import datetime

from sqlalchemy import BigInteger, ForeignKey, Index, Integer, SmallInteger, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, OperatorMixin, SoftDeleteMixin, TimestampMixin


class Contract(TimestampMixin, SoftDeleteMixin, OperatorMixin, Base):
    """合同表（sys_contract）。"""

    __tablename__ = "sys_contract"
    __table_args__ = (
        Index("ix_sys_contract_user_id", "user_id"),
        Index("ix_sys_contract_status", "status"),
        Index("ix_sys_contract_created_at", "created_at"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("sys_user.id", ondelete="RESTRICT"), nullable=False
    )
    file_name: Mapped[str] = mapped_column(String(255), nullable=False)
    file_path: Mapped[str] = mapped_column(String(512), nullable=False)
    file_ext: Mapped[str] = mapped_column(String(16), nullable=False)
    file_size: Mapped[int] = mapped_column(Integer, nullable=False)
    text_content: Mapped[str] = mapped_column(Text, nullable=False)
    total_chars: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[int] = mapped_column(SmallInteger, nullable=False, default=1)
    risk_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    high_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    medium_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    low_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)


class ContractRisk(TimestampMixin, Base):
    """合同风险结果表（sys_contract_risk）。"""

    __tablename__ = "sys_contract_risk"
    __table_args__ = (
        Index("ix_sys_contract_risk_contract_id", "contract_id"),
        Index("ix_sys_contract_risk_user_id", "user_id"),
        Index("ix_sys_contract_risk_severity", "severity"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    contract_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("sys_contract.id", ondelete="CASCADE"), nullable=False
    )
    user_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("sys_user.id", ondelete="RESTRICT"), nullable=False
    )
    rule_code: Mapped[str] = mapped_column(String(64), nullable=False)
    rule_name: Mapped[str] = mapped_column(String(128), nullable=False)
    category: Mapped[str] = mapped_column(String(32), nullable=False)
    severity: Mapped[str] = mapped_column(String(16), nullable=False)
    matched_keywords: Mapped[list[str]] = mapped_column(JSONB, nullable=False)
    risk_source: Mapped[str] = mapped_column(String(16), nullable=False, default="rule", server_default="rule")
    snippet: Mapped[str] = mapped_column(Text, nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    suggestion: Mapped[str] = mapped_column(Text, nullable=False)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)