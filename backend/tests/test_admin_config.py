"""配置中心测试：权限、加密存储、脱敏、留空保旧值、连通性测试（《05》第 3.4~3.6 节）。"""

from httpx import AsyncClient

from app.core.database import SessionFactory
from app.core.exceptions import BizException
from app.core.security import decrypt_value
from app.integrations.dingtalk import DingTalkClient
from app.models.config import SysConfig
from app.repositories.config import ConfigRepository
from tests.conftest import TEST_ADMIN_PASSWORD

VALID_CONFIG = {
    "client_id": "dingtest123",
    "client_secret": "super-secret-value-abc",
    "corp_id": "dingcorp123",
    "redirect_uri": "http://localhost:5173/dingtalk/callback",
    "enabled": True,
}


async def _read_stored_config() -> dict:
    """读取数据库中实际存储的钉钉配置（验证密文）。"""
    async with SessionFactory() as session:
        row = await ConfigRepository(session).get_by_key("dingtalk")
        assert row is not None
        return dict(row.config_value)


async def test_get_config_requires_auth(client: AsyncClient) -> None:
    """未认证访问配置返回 30000。"""
    resp = await client.get("/api/v1/admin/configs/dingtalk")
    assert resp.json()["code"] == 30000


async def test_put_config_encrypts_secret(client: AsyncClient, admin_token: str) -> None:
    """保存配置：接口返回脱敏；库中为密文（不含明文）。"""
    headers = {"Authorization": f"Bearer {admin_token}"}
    resp = await client.put("/api/v1/admin/configs/dingtalk", headers=headers, json=VALID_CONFIG)
    assert resp.status_code == 200 and resp.json()["code"] == 0
    assert "super-secret-value-abc" not in resp.json()["data"]["client_secret_masked"]

    stored = await _read_stored_config()
    assert stored["client_secret_enc"] != "super-secret-value-abc"
    assert "super-secret-value-abc" not in stored["client_secret_enc"]


async def test_put_config_keep_secret(client: AsyncClient, admin_token: str) -> None:
    """留空 client_secret 时沿用旧密文，不覆盖为明文。"""
    headers = {"Authorization": f"Bearer {admin_token}"}
    await client.put("/api/v1/admin/configs/dingtalk", headers=headers, json=VALID_CONFIG)
    stored_before = await _read_stored_config()

    payload = dict(VALID_CONFIG)
    payload["client_secret"] = ""
    resp = await client.put("/api/v1/admin/configs/dingtalk", headers=headers, json=payload)
    assert resp.status_code == 200 and resp.json()["code"] == 0

    stored_after = await _read_stored_config()
    # Fernet 非确定性加密：密文不同但解密后明文一致
    assert decrypt_value(stored_after["client_secret_enc"]) == decrypt_value(stored_before["client_secret_enc"])
    assert "super-secret-value-abc" not in stored_after["client_secret_enc"]


async def test_get_config_masks_secret(client: AsyncClient, admin_token: str) -> None:
    """读取接口返回脱敏后的 secret。"""
    headers = {"Authorization": f"Bearer {admin_token}"}
    await client.put("/api/v1/admin/configs/dingtalk", headers=headers, json=VALID_CONFIG)
    resp = await client.get("/api/v1/admin/configs/dingtalk", headers=headers)
    body = resp.json()
    assert body["code"] == 0
    assert "super-secret-value-abc" not in body["data"]["client_secret_masked"]
    assert body["data"]["client_id"] == "dingtest123"
    assert body["data"]["enabled"] is True


async def test_test_config_invalid_credentials(
    client: AsyncClient, admin_token: str, monkeypatch
) -> None:
    """连通性测试：凭据无效返回 ok=false（mock 钉钉接口，避免外部依赖）。"""
    headers = {"Authorization": f"Bearer {admin_token}"}
    await client.put("/api/v1/admin/configs/dingtalk", headers=headers, json=VALID_CONFIG)

    async def fake_get_app_token(self: DingTalkClient) -> str:
        raise BizException(30020, "钉钉授权失败")

    monkeypatch.setattr(DingTalkClient, "get_app_access_token", fake_get_app_token)
    resp = await client.post("/api/v1/admin/configs/dingtalk/test", headers=headers)
    body = resp.json()
    assert body["code"] == 0
    assert body["data"]["ok"] is False


async def test_test_config_valid_credentials(
    client: AsyncClient, admin_token: str, monkeypatch
) -> None:
    """连通性测试：凭据有效返回 ok=true。"""
    headers = {"Authorization": f"Bearer {admin_token}"}
    await client.put("/api/v1/admin/configs/dingtalk", headers=headers, json=VALID_CONFIG)

    async def fake_get_app_token(self: DingTalkClient) -> str:
        return "app-token"

    monkeypatch.setattr(DingTalkClient, "get_app_access_token", fake_get_app_token)
    resp = await client.post("/api/v1/admin/configs/dingtalk/test", headers=headers)
    body = resp.json()
    assert body["code"] == 0
    assert body["data"]["ok"] is True
async def test_get_config_normalizes_legacy_keys(
    client: AsyncClient, admin_token: str
) -> None:
    """兼容：存储为旧键（app_key/app_secret_enc）时读取归一化为新键并脱敏（《04》第 3.4 节）。"""
    from app.core.security import encrypt_value

    # 直接以旧键写入存储，模拟数据迁移前的存量配置
    async with SessionFactory() as session:
        await ConfigRepository(session).upsert(
            config_key="dingtalk",
            config_value={
                "app_key": "legacy123",
                "app_secret_enc": encrypt_value("legacy-secret-abc"),
                "redirect_uri": "http://localhost:5173/dingtalk/callback",
                "enabled": True,
                "updated_at": None,
            },
            is_encrypted=True,
            description="legacy dingtalk config",
            updated_by=1,
        )
        await session.commit()

    headers = {"Authorization": f"Bearer {admin_token}"}
    resp = await client.get("/api/v1/admin/configs/dingtalk", headers=headers)
    body = resp.json()
    assert body["code"] == 0
    assert body["data"]["client_id"] == "legacy123"
    assert "legacy-secret-abc" not in body["data"]["client_secret_masked"]


async def test_test_config_missing_corp_id(
    client: AsyncClient, admin_token: str
) -> None:
    """未填写 CorpId 时连通性测试应返回明确提示（新版应用凭证接口必须）。"""
    headers = {"Authorization": f"Bearer {admin_token}"}
    payload = dict(VALID_CONFIG)
    payload["corp_id"] = ""
    await client.put("/api/v1/admin/configs/dingtalk", headers=headers, json=payload)

    resp = await client.post("/api/v1/admin/configs/dingtalk/test", headers=headers)
    body = resp.json()
    assert body["code"] == 0
    assert body["data"]["ok"] is False
    assert "CorpId" in body["data"]["detail"]
