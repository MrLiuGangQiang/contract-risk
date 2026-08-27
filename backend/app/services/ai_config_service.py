"""AI 配置业务用例（《11-合同风险识别核心功能设计》第 2.2 节）。

配置存储于 sys_config(config_key='ai')，api_key 加密存储、读取脱敏；
测试调用 OpenAI 兼容 chat/completions 验证连通性。
"""
import logging
from datetime import datetime, timezone
from typing import Any

import httpx
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.exceptions import BizException
from app.core.security import decrypt_value, encrypt_value
from app.domain.constants import CONFIG_KEY_AI
from app.repositories.config import ConfigRepository
from app.schemas.admin import AIConfigIn, AIConfigOut, AITestResult

logger = logging.getLogger(__name__)

KEY_ENABLED = "enabled"
KEY_API_BASE = "api_base"
KEY_API_KEY_ENC = "api_key_enc"
KEY_MODEL = "model"
KEY_TIMEOUT_SECONDS = "timeout_seconds"
KEY_CONTEXT_CHARS = "context_chars"
KEY_MAX_FINDINGS = "max_findings"
KEY_UPDATED_AT = "updated_at"


def _mask(value: str) -> str:
    """敏感值脱敏：保留首尾，中间打码。"""
    if not value:
        return "***"
    if len(value) <= 8:
        return "***"
    return f"{value[:2]}***{value[-2:]}"


class AIConfigService:
    """AI 配置读取/保存/测试。"""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._config_repo = ConfigRepository(session)

    async def _stored(self) -> dict[str, Any]:
        """读取原始配置（api_key 为密文），缺失时返回默认值。"""
        row = await self._config_repo.get_by_key(CONFIG_KEY_AI)
        if row is None:
            settings = get_settings()
            return {
                KEY_ENABLED: settings.ai_enabled,
                KEY_API_BASE: settings.ai_api_base,
                KEY_API_KEY_ENC: "",
                KEY_MODEL: settings.ai_model,
                KEY_TIMEOUT_SECONDS: settings.ai_timeout_seconds,
                KEY_CONTEXT_CHARS: settings.ai_context_chars,
                KEY_MAX_FINDINGS: settings.ai_max_findings,
                KEY_UPDATED_AT: None,
            }
        return dict(row.config_value)

    async def get_plain(self) -> dict[str, Any]:
        """读取解密后的配置（仅供扫描服务，不落缓存）。"""
        value = await self._stored()
        secret_enc = value.get(KEY_API_KEY_ENC, "")
        if secret_enc:
            try:
                value[KEY_API_KEY_ENC] = decrypt_value(secret_enc)
            except ValueError as exc:
                logger.warning("AI api_key decrypt failed")
                raise BizException(50000, "AI 配置解密失败，请联系管理员") from exc
        return value

    async def get_masked(self) -> AIConfigOut:
        """读取配置并脱敏返回。"""
        value = await self.get_plain()
        secret = value.get(KEY_API_KEY_ENC) or ""
        return AIConfigOut(
            enabled=bool(value.get(KEY_ENABLED, False)),
            api_base=str(value.get(KEY_API_BASE, "")),
            api_key_masked=_mask(secret),
            model=str(value.get(KEY_MODEL, "")),
            timeout_seconds=int(value.get(KEY_TIMEOUT_SECONDS, 30)),
            context_chars=int(value.get(KEY_CONTEXT_CHARS, 30000)),
            max_findings=int(value.get(KEY_MAX_FINDINGS, 50)),
            updated_at=value.get(KEY_UPDATED_AT),
        )

    async def update(self, data: AIConfigIn, *, operator_id: int) -> AIConfigOut:
        """保存 AI 配置：api_key 留空沿用旧值（重新加密），非空则加密入库。"""
        old = await self.get_plain()
        if data.api_key:
            secret_enc = encrypt_value(data.api_key)
        elif old.get(KEY_API_KEY_ENC):
            secret_enc = encrypt_value(old[KEY_API_KEY_ENC])
        else:
            secret_enc = ""
        now = datetime.now(timezone.utc)
        value: dict[str, Any] = {
            KEY_ENABLED: data.enabled,
            KEY_API_BASE: data.api_base,
            KEY_API_KEY_ENC: secret_enc,
            KEY_MODEL: data.model,
            KEY_TIMEOUT_SECONDS: data.timeout_seconds,
            KEY_CONTEXT_CHARS: data.context_chars,
            KEY_MAX_FINDINGS: data.max_findings,
            KEY_UPDATED_AT: now.isoformat(),
        }
        await self._config_repo.upsert(
            config_key=CONFIG_KEY_AI,
            config_value=value,
            is_encrypted=True,
            description="AI 增强识别配置（api_key 已加密）",
            updated_by=operator_id,
        )
        return AIConfigOut(
            enabled=data.enabled,
            api_base=data.api_base,
            api_key_masked=_mask(data.api_key or (old.get(KEY_API_KEY_ENC, "") or "")),
            model=data.model,
            timeout_seconds=data.timeout_seconds,
            context_chars=data.context_chars,
            max_findings=data.max_findings,
            updated_at=now,
        )

    async def test(self) -> AITestResult:
        """连通性测试：调用 chat/completions 最小请求验证。"""
        value = await self.get_plain()
        api_base = str(value.get(KEY_API_BASE, "")).rstrip("/")
        api_key = value.get(KEY_API_KEY_ENC) or ""
        model = str(value.get(KEY_MODEL, ""))
        if not api_base or not api_key or not model:
            return AITestResult(ok=False, detail="请先填写 API 地址、API Key 与模型")
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.post(
                    f"{api_base}/chat/completions",
                    headers={"Authorization": f"Bearer {api_key}"},
                    json={
                        "model": model,
                        "messages": [{"role": "user", "content": "ping"}],
                        "max_tokens": 1,
                        "temperature": 0,
                    },
                )
                if resp.status_code == 200:
                    return AITestResult(ok=True, detail="AI 配置有效，已成功调用模型")
                detail = resp.text[:200]
                return AITestResult(ok=False, detail=f"调用失败：HTTP {resp.status_code} {detail}")
        except Exception as exc:
            logger.warning("AI config test failed: %s", exc)
            return AITestResult(ok=False, detail=f"连接失败：{str(exc)[:200]}")