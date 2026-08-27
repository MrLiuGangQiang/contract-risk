"""风险规则管理路由（《10-合同风险规则配置设计》第 4 节）。

权限：仅超管（risk:rule:manage）；非超管 404 隐藏。
"""
from datetime import datetime
from typing import Any

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_request_meta, require_permission
from app.core.database import get_db
from app.core.response import ApiResponse
from app.domain.constants import PERM_RISK_RULE_MANAGE
from app.models.user import User
from app.schemas.risk_rule import (
    RiskRuleCreate,
    RiskRuleImportIn,
    RiskRuleUpdate,
)
from app.services.risk_rule_service import RiskRuleService

router = APIRouter(prefix="/risk-rules", tags=["admin-risk-rules"])


@router.get("")
async def list_rules(
    request: Request,
    session: AsyncSession = Depends(get_db),
    _: User = Depends(require_permission(PERM_RISK_RULE_MANAGE, hidden=True)),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    keyword: str | None = Query(None, max_length=128),
    category: str | None = Query(None, max_length=32),
    severity: str | None = Query(None, max_length=16),
    enabled: bool | None = Query(None),
) -> dict[str, Any]:
    """风险规则分页列表。"""
    data = await RiskRuleService(session).list_rules(
        page=page, page_size=page_size, keyword=keyword,
        category=category, severity=severity, enabled=enabled,
    )
    return ApiResponse.ok(request, data=data.model_dump(mode="json"))


@router.post("")
async def create_rule(
    payload: RiskRuleCreate,
    request: Request,
    session: AsyncSession = Depends(get_db),
    user: User = Depends(require_permission(PERM_RISK_RULE_MANAGE, hidden=True)),
) -> dict[str, Any]:
    """新建风险规则。"""
    data = await RiskRuleService(session).create(
        payload, operator_id=user.id, request_meta=get_request_meta(request)
    )
    return ApiResponse.ok(request, data=data.model_dump(mode="json"))


@router.put("/{rule_id}")
async def update_rule(
    rule_id: int,
    payload: RiskRuleUpdate,
    request: Request,
    session: AsyncSession = Depends(get_db),
    user: User = Depends(require_permission(PERM_RISK_RULE_MANAGE, hidden=True)),
) -> dict[str, Any]:
    """更新风险规则。"""
    data = await RiskRuleService(session).update(
        rule_id, payload, operator_id=user.id, request_meta=get_request_meta(request)
    )
    return ApiResponse.ok(request, data=data.model_dump(mode="json"))


@router.delete("/{rule_id}")
async def delete_rule(
    rule_id: int,
    request: Request,
    session: AsyncSession = Depends(get_db),
    user: User = Depends(require_permission(PERM_RISK_RULE_MANAGE, hidden=True)),
) -> dict[str, Any]:
    """软删除风险规则。"""
    await RiskRuleService(session).delete(
        rule_id, operator_id=user.id, request_meta=get_request_meta(request)
    )
    return ApiResponse.ok(request, data=None, message="规则已删除")


@router.get("/export")
async def export_rules(
    request: Request,
    session: AsyncSession = Depends(get_db),
    _: User = Depends(require_permission(PERM_RISK_RULE_MANAGE, hidden=True)),
) -> Response:
    """导出全部规则为 Markdown 附件。"""
    content = await RiskRuleService(session).export_markdown()
    filename = f"contract-risk-rules-{datetime.now().strftime('%Y%m%d-%H%M%S')}.md"
    return Response(
        content=content,
        media_type="text/markdown; charset=utf-8",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )


@router.post("/import")
async def import_rules(
    payload: RiskRuleImportIn,
    request: Request,
    session: AsyncSession = Depends(get_db),
    user: User = Depends(require_permission(PERM_RISK_RULE_MANAGE, hidden=True)),
) -> dict[str, Any]:
    """导入 Markdown 规则（按 code 幂等 upsert）。"""
    data = await RiskRuleService(session).import_markdown(
        payload.content, operator_id=user.id, request_meta=get_request_meta(request)
    )
    return ApiResponse.ok(request, data=data.model_dump(mode="json"))
