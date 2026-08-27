"""系统配置表（sys_config）：超管配置页维护的业务可配置项（《03-数据模型设计》第 3.7 节）。"""
from typing import Any

from sqlalchemy import BigInteger, Boolean, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin


class SysConfig(TimestampMixin, Base):
    """系统配置表（sys_config）。"""

    __tablename__ = "sys_config"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    config_key: Mapped[str] = mapped_column(String(128), nullable=False, unique=True)
    config_value: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    value_type: Mapped[str] = mapped_column(
        String(32), nullable=False, default="json", server_default="json"
    )
    is_encrypted: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default="false"
    )
    description: Mapped[str | None] = mapped_column(String(512), nullable=True)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1, server_default="1")
    updated_by: Mapped[int | None] = mapped_column(BigInteger, nullable=True)