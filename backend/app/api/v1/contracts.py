"""合同风险识别路由（《11-合同风险识别核心功能设计》第 5 节）。

所有登录用户可访问，仅操作本人合同；非本人返回 404 隐藏。
"""
from typing import Any

from fastapi import APIRouter, Depends, File, Query, Request, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_request_meta
from app.core.database import get_db
from app.core.response import ApiResponse
from app.models.user import User
from app.services.contract_risk_service import ContractRiskService

router = APIRouter(prefix="/contracts", tags=["contracts"])


@router.post("/upload")
async def upload_contract(
    request: Request,
    session: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
    file: UploadFile = File(...),
) -> dict[str, Any]:
    """上传合同并同步扫描（txt/pdf/docx，≤20MB）。"""
    content = await file.read()
    data = await ContractRiskService(session).upload(
        user_id=user.id,
        file_name=file.filename or "untitled.txt",
        content=content,
        request_meta=get_request_meta(request),
    )
    return ApiResponse.ok(request, data=data.model_dump(mode="json"))


@router.get("")
async def list_contracts(
    request: Request,
    session: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    keyword: str | None = Query(None, max_length=128),
    severity: str | None = Query(None, max_length=16),
) -> dict[str, Any]:
    """合同分页列表（当前用户）。"""
    data = await ContractRiskService(session).list_contracts(
        user_id=user.id, page=page, page_size=page_size, keyword=keyword, severity=severity
    )
    return ApiResponse.ok(request, data=data.model_dump(mode="json"))


@router.get("/{contract_id}")
async def get_contract(
    contract_id: int,
    request: Request,
    session: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> dict[str, Any]:
    """合同详情 + 风险列表。"""
    data = await ContractRiskService(session).get_detail(user_id=user.id, contract_id=contract_id)
    return ApiResponse.ok(request, data=data.model_dump(mode="json"))


@router.post("/{contract_id}/rescan")
async def rescan_contract(
    contract_id: int,
    request: Request,
    session: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> dict[str, Any]:
    """重新扫描合同。"""
    data = await ContractRiskService(session).rescan(
        user_id=user.id, contract_id=contract_id, request_meta=get_request_meta(request)
    )
    return ApiResponse.ok(request, data=data.model_dump(mode="json"))


@router.delete("/{contract_id}")
async def delete_contract(
    contract_id: int,
    request: Request,
    session: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> dict[str, Any]:
    """软删除合同。"""
    await ContractRiskService(session).delete(
        user_id=user.id, contract_id=contract_id, request_meta=get_request_meta(request)
    )
    return ApiResponse.ok(request, data=None, message="合同已删除")