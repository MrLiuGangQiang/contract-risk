"""超管配置中心业务用例（含操作审计，仅敏感写操作记录）。"""
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.logs import OperationLogRepository
from app.schemas.admin import AIConfigIn, AIConfigOut, AITestResult, DingTalkConfigIn, DingTalkConfigOut, DingTalkTestResult
from app.services.ai_config_service import AIConfigService
from app.services.config_service import ConfigService


class AdminService:
    """超管配置中心：钉钉配置读写与连通性测试。"""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._config_service = ConfigService(session)
        self._ai_config_service = AIConfigService(session)
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

    # ==================== AI 配置 ====================

    async def get_ai_config(self) -> AIConfigOut:
        """Read AI config (masked)."""
        return await self._ai_config_service.get_masked()

    async def update_ai_config(
        self, data: AIConfigIn, *, operator_id: int, request_meta: dict[str, Any]
    ) -> AIConfigOut:
        """Save AI config with audit."""
        result = await self._ai_config_service.update(data, operator_id=operator_id)
        await self._operation_log_repo.add_log(
            user_id=operator_id,
            module="admin",
            action="config.ai.update",
            method="PUT",
            path="/api/v1/admin/configs/ai",
            request_body={"enabled": data.enabled, "api_base": data.api_base, "model": data.model},
            response_code=0,
            ip=request_meta.get("ip"),
            user_agent=request_meta.get("user_agent"),
            duration_ms=request_meta.get("duration_ms"),
            trace_id=request_meta.get("trace_id"),
        )
        await self._session.commit()
        return result

    async def test_ai_config(
        self, *, operator_id: int, request_meta: dict[str, Any]
    ) -> AITestResult:
        """Test AI config connectivity with audit."""
        result = await self._ai_config_service.test()
        await self._operation_log_repo.add_log(
            user_id=operator_id,
            module="admin",
            action="config.ai.test",
            method="POST",
            path="/api/v1/admin/configs/ai/test",
            request_body=None,
            response_code=0 if result.ok else 50001,
            ip=request_meta.get("ip"),
            user_agent=request_meta.get("user_agent"),
            duration_ms=request_meta.get("duration_ms"),
            trace_id=request_meta.get("trace_id"),
        )
        await self._session.commit()
        return result