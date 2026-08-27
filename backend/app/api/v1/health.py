"""健康检查（《05-API设计规范》第 2.1 节）：服务状态 + DB/Redis 连通性。"""
from typing import Any

from fastapi import APIRouter, Depends, Request
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.exceptions import BizException
from app.core.response import ApiResponse
from app.integrations import redis_client

router = APIRouter(tags=["health"])


@router.get("/health")
async def health(
    request: Request,
    session: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """健康检查：返回服务、数据库、Redis 状态（部署探针使用）。"""
    checks: dict[str, str] = {"service": "ok"}
    try:
        await session.execute(text("SELECT 1"))
        checks["database"] = "ok"
    except Exception as exc:  # pragma: no cover - 依赖外部服务
        checks["database"] = "error"
        raise BizException(50001, "数据库不可用") from exc
    try:
        await redis_client.get_redis().ping()
        checks["redis"] = "ok"
    except Exception as exc:  # pragma: no cover - 依赖外部服务
        checks["redis"] = "error"
        raise BizException(50001, "Redis 不可用") from exc
    return ApiResponse.ok(request, data=checks)