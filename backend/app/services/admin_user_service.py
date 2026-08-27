"""超管用户与角色管理业务用例（含操作审计，仅超管，接口隐藏）。

业务规则见《04-认证与授权设计》第 4.4 节：
- 禁止删除/禁用自己；
- 保护最后一个启用中的超管（is_super_admin=true 或拥有 super_admin 角色）；
- 重置密码后 must_change_password=true，并吊销全部 refresh 令牌；
- 所有写操作均写入操作审计。
"""
import logging
from typing import Any

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import BizException
from app.core.security import hash_password
from app.domain.constants import ROLE_SUPER_ADMIN, USER_STATUS_ACTIVE, USER_STATUS_DISABLED
from app.integrations import redis_client
from app.models.user import Role, User, UserRole
from app.repositories.logs import OperationLogRepository
from app.repositories.user import UserRepository
from app.schemas.admin import (
    AdminUserCreate,
    AdminUserOut,
    AdminUserPageOut,
    AdminUserResetPassword,
    AdminUserUpdate,
    RoleOut,
)

logger = logging.getLogger(__name__)


class AdminUserService:
    """超管用户与角色管理业务用例。"""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._user_repo = UserRepository(session)
        self._operation_log_repo = OperationLogRepository(session)

    # ==================== 查询 ====================

    async def list_users(
        self, *, page: int, page_size: int, keyword: str | None
    ) -> AdminUserPageOut:
        """用户分页列表（含角色）。"""
        users, total = await self._user_repo.list_users(
            page=page, page_size=page_size, keyword=keyword
        )
        items = [await self._build_out(u) for u in users]
        return AdminUserPageOut(items=items, total=total, page=page, page_size=page_size)

    async def list_roles(self) -> list[RoleOut]:
        """角色列表（分配用）。"""
        roles = await self._user_repo.list_roles()
        return [_role_out(r) for r in roles]

    # ==================== 写操作 ====================

    async def create_user(
        self,
        data: AdminUserCreate,
        *,
        operator_id: int,
        operator_is_super_admin: bool,
        request_meta: dict[str, Any],
    ) -> AdminUserOut:
        """新建用户：验证用户名唯一、角色合法、密码策略，建户后强制首次改密。"""
        if await self._user_repo.get_by_username(data.username) is not None:
            raise BizException(20001, "用户名已存在")
        roles = await self._validate_roles(data.roles)
        # 管理员可设置用户/管理员，但不可设置超管
        if not operator_is_super_admin and ROLE_SUPER_ADMIN in data.roles:
            raise BizException(40000, "仅超管可分配超管角色")
        user = User(
            username=data.username,
            password_hash=hash_password(data.password),
            display_name=data.display_name,
            status=USER_STATUS_ACTIVE,
            is_super_admin=ROLE_SUPER_ADMIN in data.roles,
            must_change_password=True,
            created_by=operator_id,
        )
        await self._user_repo.add(user)
        await self._user_repo.set_user_roles(user.id, [r.id for r in roles])
        await self._audit(
            operator_id=operator_id,
            action="user.create",
            method="POST",
            path="/api/v1/admin/users",
            request_body={"username": data.username, "roles": data.roles},
            request_meta=request_meta,
        )
        await self._session.commit()
        logger.info("admin created user", extra={"operator_id": operator_id, "user_id": user.id})
        return await self._build_out(user)

    async def update_user(
        self,
        user_id: int,
        data: AdminUserUpdate,
        *,
        operator_id: int,
        operator_is_super_admin: bool,
        request_meta: dict[str, Any],
    ) -> AdminUserOut:
        """更新用户信息与角色分配；禁止禁用自己、移除最后一个超管。"""
        user = await self._get_user_or_404(user_id)
        current_roles = await self._user_repo.get_user_roles(user_id)
        current_codes = {r.code for r in current_roles}
        if user_id == operator_id and data.status == USER_STATUS_DISABLED:
            raise BizException(40000, "不允许禁用自己")
        target_roles = await self._validate_roles(data.roles)
        target_codes = set(data.roles)
        was_super = user.is_super_admin or ROLE_SUPER_ADMIN in current_codes
        will_be_super = ROLE_SUPER_ADMIN in target_codes and data.status == USER_STATUS_ACTIVE
        # 管理员不能管理超管账号，也不能把任何人设置为超管
        if not operator_is_super_admin and was_super:
            raise BizException(40000, "仅超管可管理超管账号")
        if not operator_is_super_admin and ROLE_SUPER_ADMIN in target_codes:
            raise BizException(40000, "仅超管可分配超管角色")
        if was_super and not will_be_super:
            if await self._count_active_superadmins(exclude_user_id=user_id) == 0:
                raise BizException(40000, "不能移除最后一个启用中的超管")
        user.display_name = data.display_name
        user.status = data.status
        user.is_super_admin = ROLE_SUPER_ADMIN in target_codes
        user.updated_by = operator_id
        await self._session.flush()
        await self._user_repo.set_user_roles(user_id, [r.id for r in target_roles])
        if data.status == USER_STATUS_DISABLED:
            await redis_client.revoke_all_refresh_tokens(user_id)
        await self._audit(
            operator_id=operator_id,
            action="user.update",
            method="PUT",
            path=f"/api/v1/admin/users/{user_id}",
            request_body={"display_name": data.display_name, "status": data.status, "roles": data.roles},
            request_meta=request_meta,
        )
        await self._session.commit()
        logger.info("admin updated user", extra={"operator_id": operator_id, "user_id": user_id})
        return await self._build_out(user)

    async def reset_password(
        self,
        user_id: int,
        data: AdminUserResetPassword,
        *,
        operator_id: int,
        operator_is_super_admin: bool,
        request_meta: dict[str, Any],
    ) -> None:
        """重置密码：重置后强制改密并吊销旧会话。"""
        user = await self._get_user_or_404(user_id)
        if not operator_is_super_admin and user.is_super_admin:
            raise BizException(40000, "仅超管可重置超管账号密码")
        user.password_hash = hash_password(data.password)
        user.must_change_password = True
        user.updated_by = operator_id
        await self._session.flush()
        await redis_client.revoke_all_refresh_tokens(user_id)
        await self._audit(
            operator_id=operator_id,
            action="user.reset_password",
            method="PUT",
            path=f"/api/v1/admin/users/{user_id}/password",
            request_body=None,
            request_meta=request_meta,
        )
        await self._session.commit()
        logger.info("admin reset user password", extra={"operator_id": operator_id, "user_id": user_id})

    async def delete_user(
        self,
        user_id: int,
        *,
        operator_id: int,
        operator_is_super_admin: bool,
        request_meta: dict[str, Any],
    ) -> None:
        """软删除用户；禁止删除自己与最后一个超管。"""
        user = await self._get_user_or_404(user_id)
        if user_id == operator_id:
            raise BizException(40000, "不允许删除自己")
        roles = await self._user_repo.get_user_roles(user_id)
        codes = {r.code for r in roles}
        if not operator_is_super_admin and (user.is_super_admin or ROLE_SUPER_ADMIN in codes):
            raise BizException(40000, "仅超管可删除超管账号")
        if user.is_super_admin or ROLE_SUPER_ADMIN in codes:
            if await self._count_active_superadmins(exclude_user_id=user_id) == 0:
                raise BizException(40000, "不能删除最后一个启用中的超管")
        await self._user_repo.soft_delete_user(user)
        await redis_client.revoke_all_refresh_tokens(user_id)
        await self._audit(
            operator_id=operator_id,
            action="user.delete",
            method="DELETE",
            path=f"/api/v1/admin/users/{user_id}",
            request_body=None,
            request_meta=request_meta,
        )
        await self._session.commit()
        logger.info("admin deleted user", extra={"operator_id": operator_id, "user_id": user_id})

    # ==================== 私有辅助 ====================

    async def _build_out(self, user: User) -> AdminUserOut:
        """构建用户响应（含角色）。"""
        roles = await self._user_repo.get_user_roles(user.id)
        return AdminUserOut(
            id=user.id,
            username=user.username,
            display_name=user.display_name,
            status=user.status,
            is_super_admin=user.is_super_admin,
            must_change_password=user.must_change_password,
            roles=[_role_out(r) for r in roles],
            created_at=user.created_at,
            last_login_at=user.last_login_at,
        )

    async def _validate_roles(self, codes: list[str]) -> list[Role]:
        """验证角色编码存在且至少分配一个角色。"""
        if not codes:
            raise BizException(20001, "至少分配一个角色")
        roles = await self._user_repo.list_roles()
        by_code = {r.code: r for r in roles}
        missing = [c for c in codes if c not in by_code]
        if missing:
            raise BizException(20001, "角色不存在: " + ",".join(missing))
        return [by_code[c] for c in codes]

    async def _get_user_or_404(self, user_id: int) -> User:
        """查询用户；不存在时按不存在路由响应 404。"""
        user = await self._user_repo.get_by_id(user_id)
        if user is None:
            raise BizException(10001, "Not Found", http_status=404)
        return user

    async def _count_active_superadmins(self, *, exclude_user_id: int) -> int:
        """统计除指定用户外的活跃超管数（is_super_admin=true 或拥有 super_admin 角色）。"""
        stmt = (
            select(func.count())
            .select_from(User)
            .outerjoin(UserRole, UserRole.user_id == User.id)
            .outerjoin(Role, Role.id == UserRole.role_id)
            .where(
                User.deleted_at.is_(None),
                User.status == USER_STATUS_ACTIVE,
                User.id != exclude_user_id,
                or_(User.is_super_admin.is_(True), Role.code == ROLE_SUPER_ADMIN),
            )
        )
        return int((await self._session.execute(stmt)).scalar_one())

    async def _audit(
        self,
        *,
        operator_id: int,
        action: str,
        method: str,
        path: str,
        request_body: dict[str, Any] | None,
        request_meta: dict[str, Any],
    ) -> None:
        """写入操作审计日志。"""
        await self._operation_log_repo.add_log(
            user_id=operator_id,
            module="admin",
            action=action,
            method=method,
            path=path,
            request_body=request_body,
            response_code=0,
            ip=request_meta.get("ip"),
            user_agent=request_meta.get("user_agent"),
            duration_ms=request_meta.get("duration_ms"),
            trace_id=request_meta.get("trace_id"),
        )


def _role_out(role: Role) -> RoleOut:
    """Role 实体→ DTO。"""
    return RoleOut(
        id=role.id,
        code=role.code,
        name=role.name,
        description=role.description,
        is_builtin=role.is_builtin,
        status=role.status,
    )
