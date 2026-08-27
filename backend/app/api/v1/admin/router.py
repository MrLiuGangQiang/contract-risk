"""超管配置中心路由（《05-API设计规范》第 2.3 节）。

权限：读取/写入/测试分别对应 config:dingtalk:read / write / test。
"""
from typing import Any

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_request_meta, require_permission
from app.core.database import get_db
from app.core.response import ApiResponse
from app.domain.constants import (
    PERM_ADMIN_USER_MANAGE,
    PERM_CONFIG_DINGTALK_READ,
    PERM_CONFIG_DINGTALK_TEST,
    PERM_CONFIG_DINGTALK_WRITE,
)
from app.models.user import User
from app.schemas.admin import (
    AdminUserCreate,
    AdminUserResetPassword,
    AdminUserUpdate,
    DingTalkConfigIn,
)
from app.services.admin_service import AdminService
from app.api.v1.admin.risk_rules import router as risk_rules_router
from app.services.admin_user_service import AdminUserService

router = APIRouter(prefix="/admin", tags=["admin"])
router.include_router(risk_rules_router)


@router.get("/configs/dingtalk")
async def get_dingtalk_config(
    request: Request,
    session: AsyncSession = Depends(get_db),
    _: User = Depends(require_permission(PERM_CONFIG_DINGTALK_READ, hidden=True)),
) -> dict[str, Any]:
    """读取钉钉配置（client_secret 脱敏返回）。"""
    data = await AdminService(session).get_dingtalk_config()
    return ApiResponse.ok(request, data=data.model_dump(mode="json"))


@router.put("/configs/dingtalk")
async def update_dingtalk_config(
    payload: DingTalkConfigIn,
    request: Request,
    session: AsyncSession = Depends(get_db),
    user: User = Depends(require_permission(PERM_CONFIG_DINGTALK_WRITE, hidden=True)),
) -> dict[str, Any]:
    """保存钉钉配置（client_secret 加密入库；留空表示沿用旧值）。"""
    data = await AdminService(session).update_dingtalk_config(
        payload,
        operator_id=user.id,
        request_meta=get_request_meta(request),
    )
    return ApiResponse.ok(request, data=data.model_dump(mode="json"))


@router.post("/configs/dingtalk/test")
async def test_dingtalk_config(
    request: Request,
    session: AsyncSession = Depends(get_db),
    user: User = Depends(require_permission(PERM_CONFIG_DINGTALK_TEST, hidden=True)),
) -> dict[str, Any]:
    """连通性测试：验证 Client ID/Client Secret 是否有效。"""
    data = await AdminService(session).test_dingtalk_config(
        operator_id=user.id,
        request_meta=get_request_meta(request),
    )
    return ApiResponse.ok(request, data=data.model_dump(mode="json"))
# ==================== 用户与角色管理（《05-API设计规范》 2.4 节，非超管统一 404 隐藏） ====================

@router.get("/users")
async def list_users(
    request: Request,
    session: AsyncSession = Depends(get_db),
    _: User = Depends(require_permission(PERM_ADMIN_USER_MANAGE, hidden=True)),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    keyword: str | None = Query(None, max_length=64),
) -> dict[str, Any]:
    """用户分页列表（含角色，支持用户名/显示名模糊搜索）。"""
    data = await AdminUserService(session).list_users(page=page, page_size=page_size, keyword=keyword)
    return ApiResponse.ok(request, data=data.model_dump(mode="json"))


@router.post("/users")
async def create_user(
    payload: AdminUserCreate,
    request: Request,
    session: AsyncSession = Depends(get_db),
    user: User = Depends(require_permission(PERM_ADMIN_USER_MANAGE, hidden=True)),
) -> dict[str, Any]:
    """新建用户并分配角色；创建后强制首次改密。"""
    data = await AdminUserService(session).create_user(
        payload, operator_id=user.id, operator_is_super_admin=user.is_super_admin, request_meta=get_request_meta(request)
    )
    return ApiResponse.ok(request, data=data.model_dump(mode="json"))


@router.put("/users/{user_id}")
async def update_user(
    user_id: int,
    payload: AdminUserUpdate,
    request: Request,
    session: AsyncSession = Depends(get_db),
    user: User = Depends(require_permission(PERM_ADMIN_USER_MANAGE, hidden=True)),
) -> dict[str, Any]:
    """更新用户信息与角色分配。"""
    data = await AdminUserService(session).update_user(
        user_id, payload, operator_id=user.id, operator_is_super_admin=user.is_super_admin, request_meta=get_request_meta(request)
    )
    return ApiResponse.ok(request, data=data.model_dump(mode="json"))


@router.put("/users/{user_id}/password")
async def reset_user_password(
    user_id: int,
    payload: AdminUserResetPassword,
    request: Request,
    session: AsyncSession = Depends(get_db),
    user: User = Depends(require_permission(PERM_ADMIN_USER_MANAGE, hidden=True)),
) -> dict[str, Any]:
    """重置用户密码；重置后下次登录强制改密。"""
    await AdminUserService(session).reset_password(
        user_id, payload, operator_id=user.id, operator_is_super_admin=user.is_super_admin, request_meta=get_request_meta(request)
    )
    return ApiResponse.ok(request, data=None, message="密码已重置")


@router.delete("/users/{user_id}")
async def delete_user(
    user_id: int,
    request: Request,
    session: AsyncSession = Depends(get_db),
    user: User = Depends(require_permission(PERM_ADMIN_USER_MANAGE, hidden=True)),
) -> dict[str, Any]:
    """软删除用户并吊销其会话。"""
    await AdminUserService(session).delete_user(
        user_id, operator_id=user.id, operator_is_super_admin=user.is_super_admin, request_meta=get_request_meta(request)
    )
    return ApiResponse.ok(request, data=None, message="用户已删除")


@router.get("/roles")
async def list_roles(
    request: Request,
    session: AsyncSession = Depends(get_db),
    _: User = Depends(require_permission(PERM_ADMIN_USER_MANAGE, hidden=True)),
) -> dict[str, Any]:
    """角色列表（分配用）。"""
    data = await AdminUserService(session).list_roles()
    return ApiResponse.ok(request, data=[r.model_dump(mode="json") for r in data])

