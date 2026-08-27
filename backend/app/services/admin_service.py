"""超管配置中心业务用例（含操作审计，仅敏感写操作记录）。"""
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.logs import OperationLogRepository
from app.schemas.admin import DingTalkConfigIn, DingTalkConfigOut, DingTalkTestResult
from app.services.config_service import ConfigService


class AdminService:
    """超管配置中心：钉钉配置读写与连通性测试。"""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._config_service = ConfigService(session)
        self._operation_log_repo = OperationLogRepository(session)

    async def get_dingtalk_config(self) -> DingTalkConfigOut:
        """读取钉钉配置（脱敏返回）。"""
        return await self._config_service.get_dingtalk_config_masked()

    async def update_dingtalk_config(
        self,
        data: DingTalkConfigIn,
        *,
        operator_id: int,
        request_meta: dict[str, Any],
    ) -> DingTalkConfigOut:
        """保存钉钉配置并记录操作审计。"""
        result = await self._config_service.update_dingtalk_config(data, operator_id)
        await self._operation_log_repo.add_log(
            user_id=operator_id,
            module="admin",
            action="config.dingtalk.update",
            method="PUT",
            path="/api/v1/admin/configs/dingtalk",
            request_body={"client_id": data.client_id, "corp_id": data.corp_id, "redirect_uri": data.redirect_uri, "enabled": data.enabled},
            response_code=0,
            ip=request_meta.get("ip"),
            user_agent=request_meta.get("user_agent"),
            duration_ms=request_meta.get("duration_ms"),
            trace_id=request_meta.get("trace_id"),
        )
        await self._session.commit()
        return result

    async def test_dingtalk_config(
        self,
        *,
        operator_id: int,
        request_meta: dict[str, Any],
    ) -> DingTalkTestResult:
        """测试钉钉配置连通性并记录操作审计。"""
        result = await self._config_service.test_dingtalk_config()
        await self._operation_log_repo.add_log(
            user_id=operator_id,
            module="admin",
            action="config.dingtalk.test",
            method="POST",
            path="/api/v1/admin/configs/dingtalk/test",
            request_body=None,
            response_code=0 if result.ok else 50001,
            ip=request_meta.get("ip"),
            user_agent=request_meta.get("user_agent"),
            duration_ms=request_meta.get("duration_ms"),
            trace_id=request_meta.get("trace_id"),
        )
        await self._session.commit()
        return result