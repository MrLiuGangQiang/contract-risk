"""认证服务：本地登录、改密、登出、令牌刷新、钉钉登录全链路（《04-认证与授权设计》）。

事务边界：一个方法 = 一个事务；登录/回调内的多表写入在方法内提交。
"""
import logging
import uuid
from datetime import datetime, timezone
from typing import Any, NamedTuple

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.exceptions import BizException
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
)
from app.domain.constants import (
    DINGTALK_STATE_TTL_SECONDS,
    IDENTITY_PROVIDER_DINGTALK,
    LOGIN_FAIL_LIMIT,
    LOGIN_FAIL_LOCK_MINUTES,
    LOGIN_METHOD_DINGTALK,
    LOGIN_METHOD_DINGTALK_MICROAPP,
    LOGIN_METHOD_LOCAL,
    LOGIN_RATE_LIMIT_PER_MINUTE,
    ROLE_USER,
    USER_STATUS_ACTIVE,
)
from app.integrations import redis_client
from app.models.user import User
from app.repositories.logs import LoginLogRepository
from app.repositories.user import UserRepository
from app.schemas.auth import TokenResponse, UserOut
from app.services.config_service import ConfigService

logger = logging.getLogger(__name__)


class AuthResult(NamedTuple):
    """登录/刷新结果：响应体数据 + 需要写入 httpOnly Cookie 的 refresh token。

    refresh token 不进入响应体（《05-API设计规范》第 3.1 节），由 API 层写 Cookie。
    """

    token_response: TokenResponse
    refresh_token: str
    refresh_ttl_seconds: int


def build_user_out(user: User, roles: list[str], permissions: list[str]) -> UserOut:
    """构建用户信息 DTO（登录响应 /auth/me 复用）。"""
    return UserOut(
        id=user.id,
        username=user.username,
        display_name=user.display_name,
        avatar_url=user.avatar_url,
        is_super_admin=user.is_super_admin,
        must_change_password=user.must_change_password,
        roles=roles,
        permissions=permissions,
    )


class AuthService:
    """认证业务用例。"""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._user_repo = UserRepository(session)
        self._login_log_repo = LoginLogRepository(session)
        self._config_service = ConfigService(session)

    # ==================== 令牌 ====================

    async def _issue_tokens(self, user: User) -> AuthResult:
        """签发 access/refresh 并记录 refresh 到 Redis。"""
        settings = get_settings()
        roles = await self._user_repo.get_roles(user.id)
        permissions = await self._user_repo.get_permission_codes(user.id)
        access_token, _ = create_access_token(
            user.id, roles=roles, permissions=permissions
        )
        refresh_token, refresh_jti, refresh_ttl = create_refresh_token(user.id)
        await redis_client.save_refresh_token(user.id, refresh_jti, refresh_ttl)
        token_response = TokenResponse(
            access_token=access_token,
            expires_in=settings.access_token_expire_minutes * 60,
            user=build_user_out(user, roles, permissions),
        )
        return AuthResult(token_response, refresh_token, refresh_ttl)

    # ==================== 本地登录 ====================

    async def local_login(
        self,
        *,
        username: str,
        password: str,
        ip: str | None,
        user_agent: str | None,
        trace_id: str | None,
    ) -> AuthResult:
        """本地账密登录：限流 → 锁定校验 → 密码校验 → 签发令牌。

        失败统一返回 30010（不暴露用户是否存在）；连续失败锁定账号。
        """
        # 1) IP 限流
        if await redis_client.login_rate_exceeded(ip or "unknown", LOGIN_RATE_LIMIT_PER_MINUTE):
            raise BizException(10003, "请求过于频繁，请稍后再试")

        # 2) 账号锁定校验（按用户名 + IP 两个维度）
        for identifier in {username, ip or "unknown"}:
            if await redis_client.login_fail_locked(
                identifier, LOGIN_FAIL_LIMIT, LOGIN_FAIL_LOCK_MINUTES
            ):
                raise BizException(30013, "账号已临时锁定，请稍后再试")

        user = await self._user_repo.get_by_username(username)

        # 3) 密码校验（用户不存在时也走一次哈希校验，避免时序差异）
        password_ok = False
        if user is not None and user.password_hash:
            password_ok = verify_password(password, user.password_hash)
        if user is None or not password_ok:
            await redis_client.record_login_fail(username, LOGIN_FAIL_LIMIT, LOGIN_FAIL_LOCK_MINUTES)
            await self._login_log_repo.add_log(
                user_id=user.id if user else None,
                login_method=LOGIN_METHOD_LOCAL,
                success=False,
                fail_reason="用户名或密码错误",
                ip=ip,
                user_agent=user_agent,
                trace_id=trace_id,
            )
            await self._session.commit()
            raise BizException(30010, "用户名或密码错误")

        # 4) 状态校验
        if user.status != USER_STATUS_ACTIVE:
            await self._login_log_repo.add_log(
                user_id=user.id,
                login_method=LOGIN_METHOD_LOCAL,
                success=False,
                fail_reason="账号被禁用",
                ip=ip,
                user_agent=user_agent,
                trace_id=trace_id,
            )
            await self._session.commit()
            raise BizException(30011, "账号已被禁用")

        # 5) 成功：清除失败计数、更新最近登录、写日志、签发令牌
        await redis_client.clear_login_fail(username)
        await redis_client.clear_login_fail(ip or "unknown")
        await self._user_repo.update_last_login(user, ip)
        await self._login_log_repo.add_log(
            user_id=user.id,
            login_method=LOGIN_METHOD_LOCAL,
            success=True,
            fail_reason=None,
            ip=ip,
            user_agent=user_agent,
            trace_id=trace_id,
        )
        response = await self._issue_tokens(user)
        await self._session.commit()
        logger.info("local login success", extra={"user_id": user.id})
        return response

    # ==================== 改密 ====================

    async def change_password(
        self,
        *,
        user_id: int,
        old_password: str,
        new_password: str,
        access_jti: str,
        access_ttl_seconds: int,
    ) -> None:
        """修改密码：校验旧密码 → 更新哈希 → 强制改密标记清除 → 吊销全部旧令牌。"""
        user = await self._user_repo.get_by_id(user_id)
        if user is None or not user.password_hash or not verify_password(old_password, user.password_hash):
            raise BizException(30010, "原密码错误")

        user.password_hash = hash_password(new_password)
        user.must_change_password = False
        await self._session.flush()

        # 吊销全部旧令牌（改密后所有会话失效，须重新登录）
        await redis_client.revoke_all_refresh_tokens(user_id)
        await redis_client.blacklist_access_token(access_jti, access_ttl_seconds)
        await self._session.commit()
        logger.info("password changed", extra={"user_id": user_id})

    # ==================== 登出 ====================

    async def logout(
        self,
        *,
        user_id: int,
        access_jti: str,
        access_ttl_seconds: int,
        refresh_jti: str | None,
    ) -> None:
        """登出：吊销 access（黑名单）与 refresh（Redis 删除）。"""
        if refresh_jti:
            await redis_client.revoke_refresh_token(user_id, refresh_jti)
        await redis_client.blacklist_access_token(access_jti, access_ttl_seconds)
        logger.info("logout", extra={"user_id": user_id})

    # ==================== 令牌刷新 ====================

    async def refresh(self, refresh_token: str) -> AuthResult:
        """刷新令牌：校验 refresh 有效性 → 轮换（旧 jti 作废）→ 签发新令牌。"""
        try:
            payload = decode_token(refresh_token, "refresh")
        except Exception:
            raise BizException(30002, "令牌无效或已过期")

        user_id = int(payload.get("uid", 0))
        jti = payload.get("jti", "")
        if not await redis_client.refresh_token_exists(user_id, jti):
            raise BizException(30002, "令牌无效或已过期")

        user = await self._user_repo.get_by_id(user_id)
        if user is None or user.status != USER_STATUS_ACTIVE:
            raise BizException(30002, "令牌无效或已过期")

        # 轮换：旧 refresh 作废
        await redis_client.revoke_refresh_token(user_id, jti)
        response = await self._issue_tokens(user)
        await self._session.commit()
        return response

    # ==================== 登录方式探测 ====================

    async def login_methods(self) -> dict[str, bool]:
        """登录方式探测（公开）：钉钉配置已启用时，前端默认展示钉钉登录。"""
        value = await self._config_service.get_dingtalk_config_plain()
        return {"dingtalk_enabled": bool(value.get("enabled", False))}

    # ==================== 钉钉登录 ====================

    async def dingtalk_authorize_url(self) -> dict[str, str]:
        """生成钉钉扫码授权 URL（state 存 Redis，防 CSRF），并返回 corp_id（微应用免登 JSAPI 需要）。"""
        client = await self._config_service.build_dingtalk_client()
        state = uuid.uuid4().hex
        await redis_client.save_dingtalk_state(state, DINGTALK_STATE_TTL_SECONDS)
        return {
            "authorize_url": client.build_authorize_url(state),
            "state": state,
            "corp_id": client.corp_id,
        }

    async def dingtalk_callback(
        self,
        *,
        auth_code: str,
        state: str,
        ip: str | None,
        user_agent: str | None,
        trace_id: str | None,
    ) -> AuthResult:
        """钉钉授权回调：校验 state → 换 token → 取用户信息 → 自动建号/更新 → 签发令牌。"""
        # 1) state 防 CSRF（一次性）
        if not await redis_client.consume_dingtalk_state(state):
            await self._login_log_repo.add_log(
                user_id=None,
                login_method=LOGIN_METHOD_DINGTALK,
                success=False,
                fail_reason="state 校验失败",
                ip=ip,
                user_agent=user_agent,
                trace_id=trace_id,
            )
            await self._session.commit()
            raise BizException(30021, "登录状态已失效，请重新扫码")

        client = await self._config_service.build_dingtalk_client()

        # 2) 换取用户凭证并获取信息
        try:
            access_token = await client.exchange_code_for_token(auth_code)
            profile = await client.get_user_info(access_token)
        except BizException as exc:
            await self._login_log_repo.add_log(
                user_id=None,
                login_method=LOGIN_METHOD_DINGTALK,
                success=False,
                fail_reason=exc.message,
                ip=ip,
                user_agent=user_agent,
                trace_id=trace_id,
            )
            await self._session.commit()
            raise

        # 3) 统一身份登录（建号/更新/状态校验/日志/签发令牌，与微应用免登共用）
        return await self._login_by_dingtalk_identity(
            union_id=str(profile.get("unionId", "")),
            nick=str(profile.get("nick", "")) or "",
            avatar=profile.get("avatarUrl"),
            open_id=profile.get("openId"),
            raw_profile=profile,
            login_method=LOGIN_METHOD_DINGTALK,
            ip=ip,
            user_agent=user_agent,
            trace_id=trace_id,
        )

    async def dingtalk_microapp_login(
        self,
        *,
        auth_code: str,
        ip: str | None,
        user_agent: str | None,
        trace_id: str | None,
    ) -> AuthResult:
        """钉钉 H5 微应用免登（钉钉客户端内）：免登码换身份 → 同步资料 → 统一身份登录。

        免登码为一次性临时凭证（5 分钟有效），只在服务端与钉钉交互，不存 Redis state、
        不落库；失败由前端回退到扫码登录。与网页 OAuth 共用自动建号/签发逻辑。
        """
        client = await self._config_service.build_dingtalk_client()
        try:
            identity = await client.get_userid_by_auth_code(auth_code)
        except BizException as exc:
            await self._login_log_repo.add_log(
                user_id=None,
                login_method=LOGIN_METHOD_DINGTALK_MICROAPP,
                success=False,
                fail_reason=exc.message,
                ip=ip,
                user_agent=user_agent,
                trace_id=trace_id,
            )
            await self._session.commit()
            raise

        union_id = str(identity.get("unionid", ""))
        if not union_id:
            await self._login_log_repo.add_log(
                user_id=None,
                login_method=LOGIN_METHOD_DINGTALK_MICROAPP,
                success=False,
                fail_reason="钉钉未返回 unionid",
                ip=ip,
                user_agent=user_agent,
                trace_id=trace_id,
            )
            await self._session.commit()
            raise BizException(30020, "钉钉免登失败")

        # 头像同步为尽力而为：免登接口不返回头像，需额外权限 qyapi_get_member；
        # 未开通权限时保持原头像，不影响登录（《04》第 7 节）。
        avatar: str | None = None
        user_id = identity.get("userid")
        if user_id:
            detail = await client.get_user_detail(str(user_id))
            if detail:
                avatar = detail.get("avatar")

        return await self._login_by_dingtalk_identity(
            union_id=union_id,
            nick=str(identity.get("name", "")) or "",
            avatar=avatar,
            open_id=None,
            raw_profile=identity,
            login_method=LOGIN_METHOD_DINGTALK_MICROAPP,
            ip=ip,
            user_agent=user_agent,
            trace_id=trace_id,
        )

    async def _login_by_dingtalk_identity(
        self,
        *,
        union_id: str,
        nick: str,
        avatar: str | None,
        open_id: str | None,
        raw_profile: dict[str, Any],
        login_method: str,
        ip: str | None,
        user_agent: str | None,
        trace_id: str | None,
    ) -> AuthResult:
        """钉钉身份统一登录（网页 OAuth 与微应用免登共用）。

        按 unionId 查找/创建用户 → 同步资料 → 状态校验 → 更新登录信息 → 写日志 → 签发令牌。
        login_method 用于审计区分（dingtalk / dingtalk_microapp）。
        """
        # 1) 按 unionId 查找/创建用户
        user = await self._user_repo.get_by_union_id(IDENTITY_PROVIDER_DINGTALK, union_id)
        if user is None:
            user = await self._create_dingtalk_user(union_id, nick, avatar, open_id, raw_profile)
        else:
            # 每次登录同步昵称/头像（《04》第 7 节）
            user.display_name = nick or user.display_name
            if avatar:
                user.avatar_url = avatar
            identity = await self._user_repo.get_identity(user.id, IDENTITY_PROVIDER_DINGTALK)
            if identity is not None:
                await self._user_repo.update_identity_profile(
                    identity, open_id=open_id, raw_profile=raw_profile
                )

        # 2) 状态校验
        if user.status != USER_STATUS_ACTIVE:
            await self._login_log_repo.add_log(
                user_id=user.id,
                login_method=login_method,
                success=False,
                fail_reason="账号被禁用",
                ip=ip,
                user_agent=user_agent,
                trace_id=trace_id,
            )
            await self._session.commit()
            raise BizException(30011, "账号已被禁用")

        # 3) 成功：更新登录信息、写日志、签发令牌
        await self._user_repo.update_last_login(user, ip)
        await self._login_log_repo.add_log(
            user_id=user.id,
            login_method=login_method,
            success=True,
            fail_reason=None,
            ip=ip,
            user_agent=user_agent,
            trace_id=trace_id,
        )
        response = await self._issue_tokens(user)
        await self._session.commit()
        logger.info("dingtalk login success", extra={"user_id": user.id})
        return response

    async def _create_dingtalk_user(
        self,
        union_id: str,
        nick: str,
        avatar: str | None,
        open_id: str | None,
        profile: dict[str, Any],
    ) -> User:
        """首次钉钉登录自动建号：默认 user 角色 + 身份绑定（单事务内完成）。"""
        username = f"dt_{union_id}"[:64]
        display_name = nick or f"钉钉用户{union_id[:8]}"
        user = User(
            username=username,
            password_hash=None,
            display_name=display_name,
            avatar_url=avatar,
            status=USER_STATUS_ACTIVE,
            is_super_admin=False,
            must_change_password=False,
        )
        await self._user_repo.add(user)
        await self._user_repo.add_identity(
            user.id,
            provider=IDENTITY_PROVIDER_DINGTALK,
            union_id=union_id,
            open_id=profile.get("openId"),
            raw_profile=profile,
        )
        await self._user_repo.add_role(user.id, ROLE_USER)
        return user