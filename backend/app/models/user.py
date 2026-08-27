"""用户域模型：用户、外部身份绑定、角色、权限（《03-数据模型设计》第 3.1~3.6 节）。"""
from datetime import datetime
from typing import Any

from sqlalchemy import (
    BigInteger,
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    SmallInteger,
    String,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.domain.constants import USER_STATUS_ACTIVE
from app.models.base import Base, OperatorMixin, SoftDeleteMixin, TimestampMixin


class User(TimestampMixin, SoftDeleteMixin, OperatorMixin, Base):
    """系统用户表（sys_user）。"""

    __tablename__ = "sys_user"
    __table_args__ = (
        # 登录名唯一（软删除下用部分唯一索引保证）
        Index(
            "uq_sys_user_username",
            "username",
            unique=True,
            postgresql_where=text("deleted_at IS NULL"),
        ),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    username: Mapped[str] = mapped_column(String(64), nullable=False)
    password_hash: Mapped[str | None] = mapped_column(String(255), nullable=True)
    display_name: Mapped[str] = mapped_column(String(128), nullable=False)
    avatar_url: Mapped[str | None] = mapped_column(String(512), nullable=True)
    email: Mapped[str | None] = mapped_column(String(128), nullable=True)
    phone: Mapped[str | None] = mapped_column(String(32), nullable=True)
    status: Mapped[int] = mapped_column(
        SmallInteger, nullable=False, default=USER_STATUS_ACTIVE, server_default=text("1")
    )
    is_super_admin: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default=text("false")
    )
    must_change_password: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default=text("false")
    )
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_login_ip: Mapped[str | None] = mapped_column(String(64), nullable=True)

    identities: Mapped[list["UserIdentity"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )


class UserIdentity(TimestampMixin, Base):
    """用户外部身份绑定表（sys_user_identity），支持钉钉等多 Provider。"""

    __tablename__ = "sys_user_identity"
    __table_args__ = (
        UniqueConstraint("provider", "union_id", name="uq_sys_user_identity_provider_union"),
        Index("ix_sys_user_identity_user_id", "user_id"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("sys_user.id", ondelete="RESTRICT"), nullable=False
    )
    provider: Mapped[str] = mapped_column(String(32), nullable=False)
    union_id: Mapped[str] = mapped_column(String(128), nullable=False)
    open_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    raw_profile: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    is_bound: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, server_default=text("true")
    )

    user: Mapped[User] = relationship(back_populates="identities")


class Role(TimestampMixin, Base):
    """角色表（sys_role）。"""

    __tablename__ = "sys_role"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    code: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    description: Mapped[str | None] = mapped_column(String(512), nullable=True)
    is_builtin: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default=text("false")
    )
    status: Mapped[int] = mapped_column(
        SmallInteger, nullable=False, default=USER_STATUS_ACTIVE, server_default=text("1")
    )


class Permission(TimestampMixin, Base):
    """权限点表（sys_permission）。"""

    __tablename__ = "sys_permission"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    code: Mapped[str] = mapped_column(String(128), nullable=False, unique=True)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    module: Mapped[str] = mapped_column(String(64), nullable=False)
    description: Mapped[str | None] = mapped_column(String(512), nullable=True)


class UserRole(Base):
    """用户-角色关联表（sys_user_role），联合主键。"""

    __tablename__ = "sys_user_role"

    user_id: Mapped[int] = mapped_column(
        ForeignKey("sys_user.id", ondelete="RESTRICT"), primary_key=True
    )
    role_id: Mapped[int] = mapped_column(
        ForeignKey("sys_role.id", ondelete="RESTRICT"), primary_key=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class RolePermission(Base):
    """角色-权限关联表（sys_role_permission），联合主键。"""

    __tablename__ = "sys_role_permission"

    role_id: Mapped[int] = mapped_column(
        ForeignKey("sys_role.id", ondelete="RESTRICT"), primary_key=True
    )
    permission_id: Mapped[int] = mapped_column(
        ForeignKey("sys_permission.id", ondelete="RESTRICT"), primary_key=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )