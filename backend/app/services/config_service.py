"""配置服务：钉钉配置的读取（解密/脱敏/缓存）、更新（加密/审计）与连通性测试。

遵循《04-认证与授权设计》第 3.2 节与《06-安全设计》第 2 节：
- client_secret 加密存储（Fernet），读取脱敏；
- 配置变更失效 Redis 缓存；
- 兼容早期版本 JSON 键（app_key/app_secret_enc），读取时归一化（《04》第 3.4 节）。
"""
from datetime import datetime, timezone
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import BizException
from app.core.security import decrypt_value, encrypt_value
from app.domain.constants import CONFIG_KEY_DINGTALK
from app.integrations import redis_client
from app.integrations.dingtalk import DingTalkClient
from app.repositories.config import ConfigRepository
from app.schemas.admin import DingTalkConfigIn, DingTalkConfigOut, DingTalkTestResult

# 钉钉配置 JSON 键（加密字段带 _enc 后缀标识）
KEY_CLIENT_ID = "client_id"
KEY_CLIENT_SECRET_ENC = "client_secret_enc"
KEY_CORP_ID = "corp_id"
KEY_REDIRECT_URI = "redirect_uri"
KEY_ENABLED = "enabled"
KEY_UPDATED_AT = "updated_at"

# 早期版本键（《04》第 3.4 节：数据迁移 + 读取归一化兼容）
LEGACY_KEY_CLIENT_ID = "app_key"
LEGACY_KEY_CLIENT_SECRET_ENC = "app_secret_enc"

CONFIG_NOT_READY = 10002


def _mask(secret: str) -> str:
    """敏感值脱敏：保留首尾，中间打码。"""
    if not secret:
        return "***"
    if len(secret) <= 8:
        return "***"
    return f"{secret[:2]}***{secret[-2:]}"


def _normalize_legacy_keys(value: dict[str, Any]) -> dict[str, Any]:
    """将早期版本配置键归一化为当前键（不修改传入对象）。

    早期 sys_config 使用 app_key / app_secret_enc；数据迁移与缓存遗留场景下
    统一转换为 client_id / client_secret_enc，避免读取为空。
    """
    value = dict(value)
    if LEGACY_KEY_CLIENT_ID in value and KEY_CLIENT_ID not in value:
        value[KEY_CLIENT_ID] = value[LEGACY_KEY_CLIENT_ID]
    if LEGACY_KEY_CLIENT_SECRET_ENC in value and KEY_CLIENT_SECRET_ENC not in value:
        value[KEY_CLIENT_SECRET_ENC] = value[LEGACY_KEY_CLIENT_SECRET_ENC]
    return value


class ConfigService:
    """系统配置业务用例。"""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._config_repo = ConfigRepository(session)

    # ==================== 钉钉配置 ====================

    async def _get_stored_config(self) -> dict[str, Any]:
        """读取钉钉配置（原始存储形态：secret 为密文），优先走 Redis 缓存。

        安全约束：缓存中绝不存放明文 secret（《06-安全设计》第 2 节）。
        """
        cached = await redis_client.get_cached_config(CONFIG_KEY_DINGTALK)
        if cached is not None:
            return _normalize_legacy_keys(cached)

        row = await self._config_repo.get_by_key(CONFIG_KEY_DINGTALK)
        if row is None or not (
            row.config_value.get(KEY_CLIENT_ID) or row.config_value.get(LEGACY_KEY_CLIENT_ID)
        ):
            default: dict[str, Any] = {
                KEY_CLIENT_ID: "",
                KEY_CLIENT_SECRET_ENC: "",
                KEY_CORP_ID: "",
                KEY_REDIRECT_URI: "",
                KEY_ENABLED: False,
                KEY_UPDATED_AT: None,
            }
            return default

        value = _normalize_legacy_keys(dict(row.config_value))
        await redis_client.cache_config(CONFIG_KEY_DINGTALK, value)
        return value

    async def get_dingtalk_config_plain(self) -> dict[str, Any]:
        """读取钉钉配置（secret 解密为明文），仅用于登录/测试等内部流程，不落缓存。"""
        value = await self._get_stored_config()
        secret_enc = value.get(KEY_CLIENT_SECRET_ENC, "")
        if secret_enc:
            try:
                value[KEY_CLIENT_SECRET_ENC] = decrypt_value(secret_enc)
            except ValueError:
                raise BizException(50000, "配置解密失败，请联系管理员")
        return value

    async def get_dingtalk_config_masked(self) -> DingTalkConfigOut:
        """读取配置并脱敏返回（供配置页展示）。"""
        value = await self.get_dingtalk_config_plain()
        secret = value.get(KEY_CLIENT_SECRET_ENC) or ""  # 已解密，仅用于脱敏展示
        updated_at = value.get(KEY_UPDATED_AT)  # ISO 字符串，Pydantic 自动解析为 datetime
        return DingTalkConfigOut(
            client_id=value.get(KEY_CLIENT_ID, ""),
            client_secret_masked=_mask(secret),
            corp_id=value.get(KEY_CORP_ID, ""),
            redirect_uri=value.get(KEY_REDIRECT_URI, ""),
            enabled=bool(value.get(KEY_ENABLED, False)),
            updated_at=updated_at,
        )

    async def update_dingtalk_config(self, data: DingTalkConfigIn, operator_id: int) -> DingTalkConfigOut:
        """保存钉钉配置：client_secret 加密入库；留空表示沿用旧值。"""
        old = await self.get_dingtalk_config_plain()
        # 新值加密；留空则沿用旧值（旧明文重新加密，避免明文落库）
        if data.client_secret:
            secret_enc = encrypt_value(data.client_secret)
        elif old.get(KEY_CLIENT_SECRET_ENC):
            secret_enc = encrypt_value(old[KEY_CLIENT_SECRET_ENC])
        else:
            secret_enc = ""

        now = datetime.now(timezone.utc)
        value: dict[str, Any] = {
            KEY_CLIENT_ID: data.client_id,
            KEY_CLIENT_SECRET_ENC: secret_enc,
            KEY_CORP_ID: data.corp_id,
            KEY_REDIRECT_URI: data.redirect_uri,
            KEY_ENABLED: data.enabled,
            # JSONB 只接受可 JSON 序列化值，时间存 ISO 字符串
            KEY_UPDATED_AT: now.isoformat(),
        }
        await self._config_repo.upsert(
            config_key=CONFIG_KEY_DINGTALK,
            config_value=value,
            is_encrypted=True,
            description="钉钉登录配置（client_secret 已加密）",
            updated_by=operator_id,
        )
        # 缓存中存的是旧密文，必须失效
        await redis_client.invalidate_config_cache(CONFIG_KEY_DINGTALK)
        return DingTalkConfigOut(
            client_id=data.client_id,
            client_secret_masked=_mask(data.client_secret or (old.get(KEY_CLIENT_SECRET_ENC, "") or "")),
            corp_id=data.corp_id,
            redirect_uri=data.redirect_uri,
            enabled=data.enabled,
            updated_at=now,
        )

    async def test_dingtalk_config(self) -> DingTalkTestResult:
        """连通性测试：调用钉钉应用凭证接口验证 Client ID/Client Secret 有效性。"""
        value = await self.get_dingtalk_config_plain()
        client_id = value.get(KEY_CLIENT_ID, "")
        secret = value.get(KEY_CLIENT_SECRET_ENC, "")
        if not client_id:
            return DingTalkTestResult(ok=False, detail="请填写 Client ID")
        if not secret:
            return DingTalkTestResult(ok=False, detail="请填写 Client Secret")
        corp_id = value.get(KEY_CORP_ID, "")
        if not corp_id:
            return DingTalkTestResult(ok=False, detail="请填写企业组织 ID（CorpId）")
        client = DingTalkClient(
            client_id=client_id,
            client_secret=secret,
            corp_id=corp_id,
            redirect_uri=value.get(KEY_REDIRECT_URI, ""),
        )
        try:
            await client.get_app_access_token()
        except BizException as exc:
            # 超管连通性测试返回钉钉错误码/信息，并翻译常见错误便于定位
            detail = exc.message
            lowered = detail.lower()
            if "invalid_client" in lowered:
                detail = ("Client ID/Client Secret/CorpId 不匹配，或应用版本尚未生效："
                          "请先在应用发布 → 版本管理与发布 发布版本，并核对开发者后台首页 CorpId")
            elif "unauthorized.client" in lowered:
                detail = "应用未被授权：请确认应用已发布，并已开通基础调用权限"
            elif "unsupported.grant.type" in lowered:
                detail = "钉钉接口授权类型错误，请联系管理员检查配置"
            return DingTalkTestResult(ok=False, detail=detail)
        return DingTalkTestResult(ok=True, detail="配置有效，已成功获取钉钉应用凭证")

    async def build_dingtalk_client(self) -> DingTalkClient:
        """构造可用的钉钉客户端；未配置/未启用时抛 10002。"""
        value = await self.get_dingtalk_config_plain()
        client_id = value.get(KEY_CLIENT_ID, "")
        secret = value.get(KEY_CLIENT_SECRET_ENC, "")
        redirect_uri = value.get(KEY_REDIRECT_URI, "")
        if not client_id or not secret or not redirect_uri or not value.get(KEY_ENABLED, False):
            raise BizException(CONFIG_NOT_READY, "钉钉登录未配置或未启用")
        return DingTalkClient(
            client_id=client_id,
            client_secret=secret,
            corp_id=value.get(KEY_CORP_ID, ""),
            redirect_uri=redirect_uri,
        )
