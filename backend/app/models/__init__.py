"""ORM 模型汇总：确保 Alembic autogenerate 能发现全部表。"""
from app.models.base import Base
from app.models.config import SysConfig
from app.models.contract import Contract, ContractRisk
from app.models.log import LoginLog, OperationLog
from app.models.risk_rule import RiskRule, RiskRuleCustom
from app.models.user import (
    Permission,
    Role,
    RolePermission,
    User,
    UserIdentity,
    UserRole,
)

__all__ = [
    "Base",
    "SysConfig",
    "Contract",
    "ContractRisk",
    "LoginLog",
    "OperationLog",
    "RiskRule",
    "RiskRuleCustom",
    "User",
    "UserIdentity",
    "Role",
    "Permission",
    "UserRole",
    "RolePermission",
]