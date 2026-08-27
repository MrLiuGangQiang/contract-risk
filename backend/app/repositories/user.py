"""用户数据访问（UserRepository）。

职责边界：查询与持久化用户/身份/角色/权限数据，不含登录等业务规则。
"""
from datetime import datetime, timezone

from sqlalchemy import delete, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.constants import IDENTITY_PROVIDER_DINGTALK
from app.models.user import (
    Permission,
    Role,
    RolePermission,
    User,
    UserIdentity,
    UserRole,
)
from app.repositories.base import BaseRepository


class UserRepository(BaseRepository[User]):
    """用户及关联数据访问。"""

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session)

    async def get_by_username(self, username: str) -> User | None:
        """按登录名查询（自动过滤软删除）。"""
        stmt = select(User).where(User.username == username, User.deleted_at.is_(None))
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_id(self, user_id: int) -> User | None:
        """按主键查询（自动过滤软删除）。"""
        stmt = select(User).where(User.id == user_id, User.deleted_at.is_(None))
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_union_id(self, provider: str, union_id: str) -> User | None:
        """按外部身份（provider + union_id）反查用户。"""
        stmt = (
            select(User)
            .join(UserIdentity, UserIdentity.user_id == User.id)
            .where(
                UserIdentity.provider == provider,
                UserIdentity.union_id == union_id,
                UserIdentity.is_bound.is_(True),
                User.deleted_at.is_(None),
            )
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_identity(self, user_id: int, provider: str) -> UserIdentity | None:
        """查询用户的指定 Provider 绑定。"""
        stmt = select(UserIdentity).where(
            UserIdentity.user_id == user_id, UserIdentity.provider == provider
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_roles(self, user_id: int) -> list[str]:
        """查询用户角色编码列表。"""
        stmt = (
            select(Role.code)
            .join(UserRole, UserRole.role_id == Role.id)
            .where(UserRole.user_id == user_id, Role.status == 1)
        )
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def get_permission_codes(self, user_id: int) -> list[str]:
        """查询用户拥有的权限编码（经角色间接授权）。"""
        stmt = (
            select(Permission.code)
            .join(RolePermission, RolePermission.permission_id == Permission.id)
            .join(UserRole, UserRole.role_id == RolePermission.role_id)
            .where(UserRole.user_id == user_id)
        )
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def list_users(
        self, *, page: int, page_size: int, keyword: str | None = None
    ) -> tuple[list[User], int]:
        """用户分页列表（过滤软删除，支持用户名/显示名模糊搜索）。"""
        conditions = [User.deleted_at.is_(None)]
        if keyword:
            like = f"%{keyword}%"
            conditions.append(or_(User.username.ilike(like), User.display_name.ilike(like)))
        count_stmt = select(func.count()).select_from(User).where(*conditions)
        total = int((await self._session.execute(count_stmt)).scalar_one())
        stmt = (
            select(User)
            .where(*conditions)
            .order_by(User.id.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        users = list((await self._session.execute(stmt)).scalars().all())
        return users, total

    async def get_user_roles(self, user_id: int) -> list[Role]:
        """查询用户角色实体列表（仅活跃角色）。"""
        stmt = (
            select(Role)
            .join(UserRole, UserRole.role_id == Role.id)
            .where(UserRole.user_id == user_id, Role.status == 1)
            .order_by(Role.id)
        )
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def list_roles(self) -> list[Role]:
        """查询全部活跃角色（分配用）。"""
        stmt = select(Role).where(Role.status == 1).order_by(Role.id)
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def set_user_roles(self, user_id: int, role_ids: list[int]) -> None:
        """全量替换用户角色绑定（先删除后新增，由 Service 控制事务）。"""
        await self._session.execute(delete(UserRole).where(UserRole.user_id == user_id))
        for role_id in role_ids:
            self._session.add(UserRole(user_id=user_id, role_id=role_id))
        await self._session.flush()

    async def soft_delete_user(self, user: User) -> None:
        """软删除用户（deleted_at 置为当前时间）。"""
        user.deleted_at = datetime.now(timezone.utc)
        await self._session.flush()

    async def add_role(self, user_id: int, role_code: str) -> None:
        """为用户绑定角色（幂等：已存在则跳过）。"""
        role_stmt = select(Role).where(Role.code == role_code)
        role = (await self._session.execute(role_stmt)).scalar_one_or_none()
        if role is None:
            raise ValueError(f"role not found: {role_code}")
        exists = (
            await self._session.execute(
                select(UserRole).where(UserRole.user_id == user_id, UserRole.role_id == role.id)
            )
        ).scalar_one_or_none()
        if exists is None:
            self._session.add(UserRole(user_id=user_id, role_id=role.id))
            await self._session.flush()

    async def add_identity(
        self,
        user_id: int,
        provider: str,
        union_id: str,
        open_id: str | None,
        raw_profile: dict | None,
    ) -> UserIdentity:
        """新增外部身份绑定。"""
        identity = UserIdentity(
            user_id=user_id,
            provider=provider,
            union_id=union_id,
            open_id=open_id,
            raw_profile=raw_profile,
            is_bound=True,
        )
        self._session.add(identity)
        await self._session.flush()
        return identity

    async def update_last_login(self, user: User, ip: str | None) -> None:
        """更新最近登录时间与 IP。"""
        user.last_login_at = datetime.now(timezone.utc)
        user.last_login_ip = ip
        await self._session.flush()

    async def update_identity_profile(
        self,
        identity: UserIdentity,
        *,
        open_id: str | None,
        raw_profile: dict | None,
    ) -> None:
        """更新外部身份绑定信息（每次登录同步）。"""
        identity.open_id = open_id
        identity.raw_profile = raw_profile
        await self._session.flush()