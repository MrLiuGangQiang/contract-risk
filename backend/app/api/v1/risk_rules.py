"""个人风险规则路由（《10-合同风险规则配置设计》第 5.2 节）。

所有已登录用户可查看生效规则并维护个人副本；全局模板走 /admin/risk-rules。
"""
from typing import Any

from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.database import get_db
from app.core.response import ApiResponse
from app.models.user import User
from app.schemas.risk_rule import RiskRuleUpdate
from app.services.risk_rule_service import RiskRuleService

router = APIRouter(prefix="/risk-rules", tags=["risk-rules"])


@router.get("")
async def list_my_rules(
    request: Request,
    session: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> dict[str, Any]:
    """当前用户生效规则（全局 + 个人副本，个人优先）。"""
    data = await RiskRuleService(session).list_effective(user.id)
    return ApiResponse.ok(request, data=[r.model_dump(mode="json") for r in data])


@router.put("/me/{code}")
async def update_my_rule(
    code: str,
    payload: RiskRuleUpdate,
    request: Request,
    session: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> dict[str, Any]:
    """保存/更新当前用户个人副本。"""
    data = await RiskRuleService(session).upsert_custom(user.id, code, payload)
    return ApiResponse.ok(request, data=data.model_dump(mode="json"))


@router.delete("/me/{code}")
async def delete_my_rule(
    code: str,
    request: Request,
    session: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> dict[str, Any]:
    """恢复单条默认：删除当前用户该规则个人副本。"""
    await RiskRuleService(session).delete_custom(user.id, code)
    return ApiResponse.ok(request, data=None, message="已恢复默认")


@router.post("/me/restore-default")
async def restore_default(
    request: Request,
    session: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> dict[str, Any]:
    """一键恢复默认：删除当前用户全部个人副本（前端需确认）。"""
    await RiskRuleService(session).restore_default(user.id)
    return ApiResponse.ok(request, data=None, message="已恢复为全局默认")