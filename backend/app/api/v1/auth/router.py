"""认证路由：本地登录/改密/登出/刷新、钉钉登录、当前用户（《05-API设计规范》第 2.2 节）。"""
from typing import Any

from fastapi import APIRouter, Depends, Request, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.config import get_settings
from app.core.database import get_db
from app.core.exceptions import BizException
from app.core.response import ApiResponse
from app.core.security import decode_token
from app.models.user import User
from app.repositories.user import UserRepository
from app.schemas.auth import (
    ChangePasswordRequest,
    DingtalkAuthorizeResponse,
    DingtalkCallbackRequest,
    LoginMethodsResponse,
    LoginRequest,
    TokenResponse,
)
from app.services.auth_service import AuthService, build_user_out

router = APIRouter(prefix="/auth", tags=["auth"])

REFRESH_COOKIE = "refresh_token"


def _set_refresh_cookie(response: Response, token: str, ttl_seconds: int) -> None:
    """下发 refresh token：httpOnly + SameSite=Lax；生产环境追加 Secure。

    遵循《06-安全设计》第 3 节：refresh 不出现在响应体，仅存 Cookie。
    """
    settings = get_settings()
    response.set_cookie(
        key=REFRESH_COOKIE,
        value=token,
        max_age=ttl_seconds,
        httponly=True,
        secure=settings.app_env == "prod",
        samesite="lax",
        path="/api/v1/auth",
    )


def _clear_refresh_cookie(response: Response) -> None:
    """清除 refresh cookie（登出时调用）。"""
    response.delete_cookie(REFRESH_COOKIE, path="/api/v1/auth")


def _refresh_jti_from_cookie(request: Request) -> str | None:
    """从 Cookie 中解析 refresh token 的 jti（解析失败返回 None）。"""
    token = request.cookies.get(REFRESH_COOKIE)
    if not token:
        return None
    try:
        return decode_token(token, "refresh").get("jti")
    except Exception:
        return None


@router.get("/login-methods")
async def login_methods(
    request: Request,
    session: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """登录方式探测（公开）：钉钉配置已启用时返回 true，前端默认展示钉钉登录。"""
    data = await AuthService(session).login_methods()
    return ApiResponse.ok(request, data=LoginMethodsResponse(**data).model_dump())


@router.post("/login")
async def local_login(
    payload: LoginRequest,
    request: Request,
    response: Response,
    session: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """本地账密登录（超管初始账号）。"""
    result = await AuthService(session).local_login(
        username=payload.username,
        password=payload.password,
        ip=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
        trace_id=getattr(request.state, "request_id", None),
    )
    _set_refresh_cookie(response, result.refresh_token, result.refresh_ttl_seconds)
    return ApiResponse.ok(request, data=result.token_response.model_dump(mode="json"))


@router.post("/change-password")
async def change_password(
    payload: ChangePasswordRequest,
    request: Request,
    session: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> dict[str, Any]:
    """修改密码（首次登录强制改密也走此接口）。"""
    await AuthService(session).change_password(
        user_id=user.id,
        old_password=payload.old_password,
        new_password=payload.new_password,
        access_jti=getattr(request.state, "access_jti", ""),
        access_ttl_seconds=getattr(request.state, "access_ttl_seconds", 0),
    )
    return ApiResponse.ok(request, data=None, message="密码修改成功")


@router.post("/logout")
async def logout(
    request: Request,
    response: Response,
    session: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> dict[str, Any]:
    """登出：吊销当前会话令牌并清除 Cookie。"""
    await AuthService(session).logout(
        user_id=user.id,
        access_jti=getattr(request.state, "access_jti", ""),
        access_ttl_seconds=getattr(request.state, "access_ttl_seconds", 0),
        refresh_jti=_refresh_jti_from_cookie(request),
    )
    _clear_refresh_cookie(response)
    return ApiResponse.ok(request, data=None, message="已登出")


@router.post("/refresh")
async def refresh(
    request: Request,
    response: Response,
    session: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """刷新令牌（轮换）：refresh token 从 httpOnly Cookie 读取。"""
    token = request.cookies.get(REFRESH_COOKIE)
    if not token:
        raise BizException(30002, "令牌无效或已过期")
    result = await AuthService(session).refresh(token)
    _set_refresh_cookie(response, result.refresh_token, result.refresh_ttl_seconds)
    return ApiResponse.ok(request, data=result.token_response.model_dump(mode="json"))


@router.get("/dingtalk/authorize-url")
async def dingtalk_authorize_url(
    request: Request,
    session: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """获取钉钉扫码授权 URL（公开接口；未配置/未启用返回 10002）。"""
    data = await AuthService(session).dingtalk_authorize_url()
    return ApiResponse.ok(request, data=DingtalkAuthorizeResponse(**data).model_dump())


@router.post("/dingtalk/callback")
async def dingtalk_callback(
    payload: DingtalkCallbackRequest,
    request: Request,
    response: Response,
    session: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """钉钉授权回调：前端携带 authCode + state 换取登录态。"""
    result = await AuthService(session).dingtalk_callback(
        auth_code=payload.auth_code,
        state=payload.state,
        ip=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
        trace_id=getattr(request.state, "request_id", None),
    )
    _set_refresh_cookie(response, result.refresh_token, result.refresh_ttl_seconds)
    return ApiResponse.ok(request, data=result.token_response.model_dump(mode="json"))


@router.get("/me")
async def me(
    request: Request,
    session: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> dict[str, Any]:
    """当前用户信息（含角色与权限，实时从数据库读取）。"""
    repo = UserRepository(session)
    roles = await repo.get_roles(user.id)
    permissions = await repo.get_permission_codes(user.id)
    return ApiResponse.ok(request, data=build_user_out(user, roles, permissions).model_dump())