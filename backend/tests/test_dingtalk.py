"""钉钉登录测试：未配置拦截、授权 URL、state 校验、全链路登录（mock 钉钉接口）。"""

from httpx import AsyncClient

from app.core.database import SessionFactory
from app.domain.constants import IDENTITY_PROVIDER_DINGTALK, USER_STATUS_DISABLED
from app.integrations.dingtalk import DingTalkClient
from app.models.user import User, UserIdentity
from app.repositories.user import UserRepository

CONFIG = {
    "client_id": "dingapp123",
    "client_secret": "ding-secret-abc",
    "corp_id": "dingcorp123",
    "redirect_uri": "http://localhost:5173/dingtalk/callback",
    "enabled": True,
}


async def _configure_dingtalk(client: AsyncClient, admin_token: str) -> None:
    resp = await client.put(
        "/api/v1/admin/configs/dingtalk",
        headers={"Authorization": f"Bearer {admin_token}"},
        json=CONFIG,
    )
    assert resp.status_code == 200 and resp.json()["code"] == 0


async def _mock_dingtalk_apis(monkeypatch, *, nick: str = "张三", union_id: str = "u123") -> None:
    """mock 钉钉换 token 与用户信息接口。"""

    async def fake_exchange(self: DingTalkClient, auth_code: str) -> str:
        assert auth_code == "valid-code"
        return "user-access-token"

    async def fake_user_info(self: DingTalkClient, access_token: str) -> dict:
        assert access_token == "user-access-token"
        return {"unionId": union_id, "nick": nick, "avatarUrl": "http://avatar/1.png", "openId": "open123"}

    monkeypatch.setattr(DingTalkClient, "exchange_code_for_token", fake_exchange)
    monkeypatch.setattr(DingTalkClient, "get_user_info", fake_user_info)


async def _get_state(client: AsyncClient, admin_token: str) -> str:
    resp = await client.get("/api/v1/auth/dingtalk/authorize-url")
    assert resp.status_code == 200 and resp.json()["code"] == 0
    return resp.json()["data"]["state"]


async def test_authorize_url_not_configured(client: AsyncClient, fresh_admin) -> None:
    """未配置钉钉时获取授权 URL 返回 10002。"""
    resp = await client.get("/api/v1/auth/dingtalk/authorize-url")
    assert resp.json()["code"] == 10002


async def test_authorize_url_after_configure(client: AsyncClient, admin_token: str) -> None:
    """配置后授权 URL 应包含 client_id/redirect_uri/state。"""
    await _configure_dingtalk(client, admin_token)
    resp = await client.get("/api/v1/auth/dingtalk/authorize-url")
    body = resp.json()
    assert body["code"] == 0
    url = body["data"]["authorize_url"]
    assert url.startswith("https://login.dingtalk.com/oauth2/auth")
    assert "client_id=dingapp123" in url
    assert "state=" in url


async def test_callback_invalid_state(client: AsyncClient, admin_token: str) -> None:
    """state 无效/被消费后回调应返回 30021。"""
    await _configure_dingtalk(client, admin_token)
    resp = await client.post(
        "/api/v1/auth/dingtalk/callback", json={"auth_code": "x", "state": "not-exists"}
    )
    assert resp.json()["code"] == 30021


async def test_dingtalk_callback_creates_user(
    client: AsyncClient, admin_token: str, monkeypatch
) -> None:
    """首次钉钉登录：自动建号 + 身份绑定 + user 角色 + 签发令牌。"""
    await _configure_dingtalk(client, admin_token)
    await _mock_dingtalk_apis(monkeypatch)
    state = await _get_state(client, admin_token)

    resp = await client.post(
        "/api/v1/auth/dingtalk/callback",
        json={"auth_code": "valid-code", "state": state},
    )
    body = resp.json()
    assert resp.status_code == 200 and body["code"] == 0, body
    assert body["data"]["user"]["username"].startswith("dt_u123")
    assert body["data"]["user"]["display_name"] == "张三"
    assert body["data"]["user"]["is_super_admin"] is False
    assert body["data"]["user"]["must_change_password"] is False
    assert body["data"]["user"]["roles"] == ["user"]
    assert "refresh_token" in resp.cookies

    # 数据库校验：用户 + 身份绑定
    async with SessionFactory() as session:
        user = await UserRepository(session).get_by_union_id(IDENTITY_PROVIDER_DINGTALK, "u123")
        assert user is not None and user.display_name == "张三"


async def test_dingtalk_callback_updates_profile(
    client: AsyncClient, admin_token: str, monkeypatch
) -> None:
    """再次登录应同步更新昵称/头像。"""
    await _configure_dingtalk(client, admin_token)
    await _mock_dingtalk_apis(monkeypatch, nick="李四", union_id="u456")

    state = await _get_state(client, admin_token)
    resp = await client.post(
        "/api/v1/auth/dingtalk/callback", json={"auth_code": "valid-code", "state": state}
    )
    assert resp.json()["code"] == 0
    assert resp.json()["data"]["user"]["display_name"] == "李四"

    # 第二次登录，昵称变化
    await _mock_dingtalk_apis(monkeypatch, nick="李四改", union_id="u456")
    state = await _get_state(client, admin_token)
    resp = await client.post(
        "/api/v1/auth/dingtalk/callback", json={"auth_code": "valid-code", "state": state}
    )
    assert resp.json()["code"] == 0
    assert resp.json()["data"]["user"]["display_name"] == "李四改"

    async with SessionFactory() as session:
        user = await UserRepository(session).get_by_union_id(IDENTITY_PROVIDER_DINGTALK, "u456")
        assert user is not None and user.display_name == "李四改"


async def test_dingtalk_callback_disabled_user_rejected(
    client: AsyncClient, admin_token: str, monkeypatch
) -> None:
    """被禁用的钉钉用户登录应返回 30011。"""
    await _configure_dingtalk(client, admin_token)
    await _mock_dingtalk_apis(monkeypatch, union_id="u999")

    # 预置禁用用户 + 绑定
    async with SessionFactory() as session:
        user = User(
            username="dt_u999",
            display_name="禁用用户",
            status=USER_STATUS_DISABLED,
            is_super_admin=False,
        )
        session.add(user)
        await session.flush()
        session.add(
            UserIdentity(
                user_id=user.id,
                provider=IDENTITY_PROVIDER_DINGTALK,
                union_id="u999",
                is_bound=True,
            )
        )
        await session.commit()

    state = await _get_state(client, admin_token)
    resp = await client.post(
        "/api/v1/auth/dingtalk/callback", json={"auth_code": "valid-code", "state": state}
    )
    assert resp.json()["code"] == 30011


async def test_dingtalk_callback_state_single_use(
    client: AsyncClient, admin_token: str, monkeypatch
) -> None:
    """state 一次性：重复使用应失败。"""
    await _configure_dingtalk(client, admin_token)
    await _mock_dingtalk_apis(monkeypatch)
    state = await _get_state(client, admin_token)

    resp = await client.post(
        "/api/v1/auth/dingtalk/callback", json={"auth_code": "valid-code", "state": state}
    )
    assert resp.json()["code"] == 0
    resp = await client.post(
        "/api/v1/auth/dingtalk/callback", json={"auth_code": "valid-code", "state": state}
    )
    assert resp.json()["code"] == 30021


class _FakeTokenResponse:
    """模拟钉钉新接口成功响应。"""

    status_code = 200

    def json(self) -> dict:
        return {"access_token": "app-token"}

    def raise_for_status(self) -> None:
        return None


class _FakeTokenClient:
    """模拟 httpx.AsyncClient，捕获请求 URL 与 body。"""

    def __init__(self, *, captured: dict) -> None:
        self._captured = captured

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args) -> None:
        return None

    async def post(self, url: str, json: dict) -> _FakeTokenResponse:
        self._captured["url"] = url
        self._captured["json"] = dict(json)
        return _FakeTokenResponse()


async def test_app_access_token_uses_new_api(monkeypatch) -> None:
    """应用凭证必须调用最新 /v1.0/oauth2/{corpId}/token，body 使用 client_id/client_secret。"""
    captured: dict = {}

    def fake_client(*args, **kwargs):
        return _FakeTokenClient(captured=captured)

    monkeypatch.setattr("app.integrations.dingtalk.httpx.AsyncClient", fake_client)
    client = DingTalkClient(
        client_id="ding123",
        client_secret="ding-secret",
        corp_id="dingcorp123",
        redirect_uri="http://localhost:5173/dingtalk/callback",
    )
    token = await client.get_app_access_token()
    assert token == "app-token"
    assert captured["url"] == "https://api.dingtalk.com/v1.0/oauth2/dingcorp123/token"
    assert captured["json"] == {
        "client_id": "ding123",
        "client_secret": "ding-secret",
        "grant_type": "client_credentials",
    }
