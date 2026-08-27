"""公共 API 依赖：当前用户解析、权限校验（《04-认证与授权设计》第 4.2 节）。"""
from datetime import datetime, timezone
from typing import Any

from fastapi import Depends, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.exceptions import BizException
from app.core.security import decode_token
from app.domain.constants import USER_STATUS_ACTIVE
from app.integrations import redis_client
from app.models.user import User
from app.repositories.user import UserRepository

bearer_scheme = HTTPBearer(auto_error=False)

# 强制改密拦截白名单（这些端点允许在 must_change_password 时访问）
PASSWORD_CHANGE_WHITELIST = {
    "/api/v1/auth/change-password",
    "/api/v1/auth/logout",
    "/api/v1/auth/refresh",
    "/api/v1/auth/me",
}


async def get_current_user(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    session: AsyncSession = Depends(get_db),
) -> User:
    """解析 access token 并返回当前用户；失败统一抛 300xx 业务异常。"""
    if credentials is None:
        raise BizException(30000, "未认证")

    try:
        payload = decode_token(credentials.credentials, "access")
    except Exception:
        raise BizException(30002, "令牌无效或已过期")

    jti = payload.get("jti", "")
    if await redis_client.is_access_token_blacklisted(jti):
        raise BizException(30002, "令牌无效或已过期")

    user = await UserRepository(session).get_by_id(int(payload.get("uid", 0)))
    if user is None or user.status != USER_STATUS_ACTIVE:
        raise BizException(30011, "账号已被禁用")

    # 首次登录强制改密：仅放行白名单端点
    if user.must_change_password and request.url.path not in PASSWORD_CHANGE_WHITELIST:
        raise BizException(30012, "首次登录需修改密码")

    exp = payload.get("exp")
    ttl = max(0, int(exp) - int(datetime.now(timezone.utc).timestamp())) if exp else 0

    request.state.user = user
    request.state.access_jti = jti
    request.state.access_ttl_seconds = ttl
    request.state.permissions: list[str] = payload.get("permissions", []) or []
    return user


def require_permission(code: str, *, hidden: bool = False) -> Any:
    """权限校验依赖工厂：超管直接放行，否则校验 token 中的权限编码。
    hidden=True（敏感管理端点）：无权限时统一按 404（Not Found）响应，与不存在路由完全一致，避免暴露接口存在性。"""

    async def checker(
        request: Request,
        user: User = Depends(get_current_user),
    ) -> User:
        if user.is_super_admin:
            return user
        permissions: list[str] = getattr(request.state, "permissions", []) or []
        if code not in permissions:
            if hidden:
                # 完全隐藏：无权限按 404 响应，避免暴露敏感管理接口
                raise BizException(10001, "Not Found", http_status=404)
            raise BizException(40000, "无权限")
        return user
    return checker

def get_request_meta(request: Request) -> dict[str, Any]:
    """提取请求元信息（IP/UA/trace_id/耗时），供审计日志使用。"""
    import time as _time

    start = getattr(request.state, "start_time", None)
    duration_ms = int((_time.perf_counter() - start) * 1000) if start else None
    return {
        "ip": request.client.host if request.client else None,
        "user_agent": request.headers.get("user-agent"),
        "trace_id": getattr(request.state, "request_id", None),
        "duration_ms": duration_ms,
    }