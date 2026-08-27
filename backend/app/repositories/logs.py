"""审计日志数据访问：登录日志、操作日志（只增不改）。"""
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.log import LoginLog, OperationLog
from app.repositories.base import BaseRepository


class LoginLogRepository(BaseRepository[LoginLog]):
    """登录日志写入。"""

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session)

    async def add_log(
        self,
        *,
        user_id: int | None,
        login_method: str,
        success: bool,
        fail_reason: str | None,
        ip: str | None,
        user_agent: str | None,
        trace_id: str | None,
    ) -> None:
        """写入一条登录日志（不提交，由 Service 控制事务）。"""
        self._session.add(
            LoginLog(
                user_id=user_id,
                login_method=login_method,
                success=success,
                fail_reason=fail_reason,
                ip=ip,
                user_agent=user_agent,
                trace_id=trace_id,
            )
        )
        await self._session.flush()


class OperationLogRepository(BaseRepository[OperationLog]):
    """操作审计日志写入。"""

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session)

    async def add_log(
        self,
        *,
        user_id: int | None,
        module: str,
        action: str,
        method: str,
        path: str,
        request_body: dict[str, Any] | None,
        response_code: int | None,
        ip: str | None,
        user_agent: str | None,
        duration_ms: int | None,
        trace_id: str | None,
    ) -> None:
        """写入一条操作日志（不提交，由 Service 控制事务）。"""
        self._session.add(
            OperationLog(
                user_id=user_id,
                module=module,
                action=action,
                method=method,
                path=path,
                request_body=request_body,
                response_code=response_code,
                ip=ip,
                user_agent=user_agent,
                duration_ms=duration_ms,
                trace_id=trace_id,
            )
        )
        await self._session.flush()