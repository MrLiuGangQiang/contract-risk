"""启动引导（幂等）：种子角色/权限/配置 + 初始超管创建（《03-数据模型设计》第 4 节）。

- 首次启动创建内置角色与权限点；
- 超管账号来自环境变量 ADMIN_USERNAME/ADMIN_PASSWORD，must_change_password=true；
- 初始密码未达策略时记录告警（仍允许创建，由首次登录强制改密兜底）；
- 幂等：重复执行不产生重复数据。
"""
import logging
import re

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.security import hash_password
from app.domain.constants import (
    CONFIG_KEY_DINGTALK,
    PERM_AUTH_LOGIN,
    PERM_AUTH_ME,
    PERM_CONFIG_DINGTALK_READ,
    PERM_CONFIG_DINGTALK_TEST,
    PERM_CONFIG_DINGTALK_WRITE,
    PERM_ADMIN_USER_MANAGE,
    PERM_RISK_RULE_MANAGE,
    ROLE_ADMIN,
    ROLE_SUPER_ADMIN,
    ROLE_USER,
    USER_STATUS_ACTIVE,
)
from app.domain.default_risk_rules import DEFAULT_RISK_RULES
from app.models.config import SysConfig
from app.models.risk_rule import RiskRule
from app.models.user import Permission, Role, RolePermission, User, UserRole

logger = logging.getLogger(__name__)

# 权限点种子：(编码, 名称, 模块)
SEED_PERMISSIONS = [
    (PERM_AUTH_LOGIN, "登录", "auth"),
    (PERM_AUTH_ME, "查看当前用户", "auth"),
    (PERM_CONFIG_DINGTALK_READ, "读取钉钉配置", "admin"),
    (PERM_CONFIG_DINGTALK_WRITE, "保存钉钉配置", "admin"),
    (PERM_CONFIG_DINGTALK_TEST, "测试钉钉配置", "admin"),
    (PERM_ADMIN_USER_MANAGE, "用户与角色管理", "admin"),
    (PERM_RISK_RULE_MANAGE, "风险规则管理", "risk"),
]

# 角色 → 权限编码
SEED_ROLE_PERMISSIONS = {
    ROLE_SUPER_ADMIN: [code for code, _, _ in SEED_PERMISSIONS],
    # 管理员：仅用户与角色管理，不含超管配置（钉钉配置仍仅超管）
    ROLE_ADMIN: [PERM_AUTH_LOGIN, PERM_AUTH_ME, PERM_ADMIN_USER_MANAGE, PERM_RISK_RULE_MANAGE],
    ROLE_USER: [PERM_AUTH_LOGIN, PERM_AUTH_ME],
}


async def _ensure_role(session: AsyncSession, code: str, name: str) -> Role:
    role = (
        await session.execute(select(Role).where(Role.code == code))
    ).scalar_one_or_none()
    if role is None:
        role = Role(code=code, name=name, description="内置角色", is_builtin=True, status=USER_STATUS_ACTIVE)
        session.add(role)
        await session.flush()
    return role


async def _ensure_permissions(session: AsyncSession) -> dict[str, Permission]:
    result = {}
    for code, name, module in SEED_PERMISSIONS:
        perm = (
            await session.execute(select(Permission).where(Permission.code == code))
        ).scalar_one_or_none()
        if perm is None:
            perm = Permission(code=code, name=name, module=module)
            session.add(perm)
            await session.flush()
        result[code] = perm
    return result


async def _ensure_role_permissions(session: AsyncSession, roles: dict[str, Role], perms: dict[str, Permission]) -> None:
    for role_code, perm_codes in SEED_ROLE_PERMISSIONS.items():
        role = roles[role_code]
        for code in perm_codes:
            exists = (
                await session.execute(
                    select(RolePermission).where(
                        RolePermission.role_id == role.id,
                        RolePermission.permission_id == perms[code].id,
                    )
                )
            ).scalar_one_or_none()
            if exists is None:
                session.add(RolePermission(role_id=role.id, permission_id=perms[code].id))
    await session.flush()


async def _ensure_dingtalk_config(session: AsyncSession) -> None:
    exists = (
        await session.execute(select(SysConfig).where(SysConfig.config_key == CONFIG_KEY_DINGTALK))
    ).scalar_one_or_none()
    if exists is None:
        session.add(
            SysConfig(
                config_key=CONFIG_KEY_DINGTALK,
                config_value={
                    "client_id": "",
                    "client_secret_enc": "",
                    "corp_id": "",
                    "redirect_uri": "",
                    "enabled": False,
                    "updated_at": None,
                },
                value_type="json",
                is_encrypted=True,
                description="钉钉登录配置（client_secret 已加密）",
                version=1,
                updated_by=None,
            )
        )
        await session.flush()


def _password_meets_policy(password: str) -> bool:
    """判断初始密码是否满足《04-认证与授权设计》第 8 节密码策略（长度 + 至少三类字符）。"""
    if len(password) < 10:
        return False
    classes = 0
    if re.search(r"[a-z]", password):
        classes += 1
    if re.search(r"[A-Z]", password):
        classes += 1
    if re.search(r"\d", password):
        classes += 1
    if re.search(r"[^a-zA-Z0-9]", password):
        classes += 1
    return classes >= 3


async def _ensure_admin_user(session: AsyncSession) -> None:
    """按环境变量创建初始超管（幂等）；密码不满足策略时记录告警但允许创建（首次登录强制改密）。"""
    settings = get_settings()
    if not _password_meets_policy(settings.admin_password):
        logger.warning(
            "initial admin password does not meet the password policy; "
            "first login will be forced to change password"
        )
    admin = (
        await session.execute(
            select(User).where(User.username == settings.admin_username, User.deleted_at.is_(None))
        )
    ).scalar_one_or_none()
    if admin is not None:
        return
    admin = User(
        username=settings.admin_username,
        password_hash=hash_password(settings.admin_password),
        display_name="超级管理员",
        status=USER_STATUS_ACTIVE,
        is_super_admin=True,
        must_change_password=True,
    )
    session.add(admin)
    await session.flush()
    roles = (
        await session.execute(select(Role).where(Role.code == ROLE_SUPER_ADMIN))
    ).scalar_one_or_none()
    if roles is not None:
        session.add(UserRole(user_id=admin.id, role_id=roles.id))
    await session.flush()
    logger.info("initial super admin created: %s", settings.admin_username)


async def _ensure_default_risk_rules(session: AsyncSession) -> None:
    """Seed default risk rules when the global rule set is empty.

    Idempotent: does nothing if any active global rule exists.
    """
    existing = (
        await session.execute(
            select(RiskRule.id).where(RiskRule.deleted_at.is_(None)).limit(1)
        )
    ).scalar_one_or_none()
    if existing is not None:
        return
    for item in DEFAULT_RISK_RULES:
        session.add(RiskRule(**item))
    await session.flush()
    logger.info("default risk rules seeded: %s", len(DEFAULT_RISK_RULES))


async def bootstrap(session: AsyncSession) -> None:
    """执行全部启动引导（应用启动时调用，幂等）。"""
    roles = {
        ROLE_SUPER_ADMIN: await _ensure_role(session, ROLE_SUPER_ADMIN, "超管"),
        ROLE_ADMIN: await _ensure_role(session, ROLE_ADMIN, "管理员"),
        ROLE_USER: await _ensure_role(session, ROLE_USER, "普通用户"),
    }
    perms = await _ensure_permissions(session)
    await _ensure_role_permissions(session, roles, perms)
    await _ensure_dingtalk_config(session)
    await _ensure_admin_user(session)
    await _ensure_default_risk_rules(session)
    await session.commit()
    logger.info("bootstrap finished")