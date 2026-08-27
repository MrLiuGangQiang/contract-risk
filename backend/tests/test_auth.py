"""认证链路测试：登录、强制改密、令牌吊销、刷新轮换、RBAC（《04-认证与授权设计》）。"""

from httpx import AsyncClient

from tests.conftest import TEST_ADMIN_PASSWORD, TEST_ADMIN_USERNAME

NEW_PASSWORD = "Test@12345678"


async def test_login_wrong_password_fails(client: AsyncClient, fresh_admin) -> None:
    """错误密码应返回统一错误码 30010，且不泄露用户是否存在。"""
    resp = await client.post(
        "/api/v1/auth/login",
        json={"username": TEST_ADMIN_USERNAME, "password": "wrong-password"},
    )
    assert resp.status_code == 400
    body = resp.json()
    assert body["code"] == 30010
    assert body["data"] is None


async def test_login_success_requires_password_change(client: AsyncClient, fresh_admin) -> None:
    """初始超管登录成功，但 must_change_password=true，且带 refresh cookie。"""
    resp = await client.post(
        "/api/v1/auth/login",
        json={"username": TEST_ADMIN_USERNAME, "password": TEST_ADMIN_PASSWORD},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["code"] == 0
    assert body["data"]["user"]["must_change_password"] is True
    assert body["data"]["user"]["is_super_admin"] is True
    assert "refresh_token" in resp.cookies


async def test_must_change_password_blocks_admin_api(client: AsyncClient, fresh_admin) -> None:
    """未改密前访问管理端接口应被拦截（30012）。"""
    resp = await client.post(
        "/api/v1/auth/login",
        json={"username": TEST_ADMIN_USERNAME, "password": TEST_ADMIN_PASSWORD},
    )
    token = resp.json()["data"]["access_token"]
    resp = await client.get(
        "/api/v1/admin/configs/dingtalk",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.json()["code"] == 30012


async def test_change_password_revokes_all_tokens(client: AsyncClient, fresh_admin) -> None:
    """改密成功后：旧 access 与旧 refresh 全部失效，新密码可登录。"""
    resp = await client.post(
        "/api/v1/auth/login",
        json={"username": TEST_ADMIN_USERNAME, "password": TEST_ADMIN_PASSWORD},
    )
    token = resp.json()["data"]["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    resp = await client.post(
        "/api/v1/auth/change-password",
        headers=headers,
        json={"old_password": TEST_ADMIN_PASSWORD, "new_password": NEW_PASSWORD},
    )
    assert resp.status_code == 200 and resp.json()["code"] == 0

    # 旧 access 已吊销
    resp = await client.get("/api/v1/auth/me", headers=headers)
    assert resp.json()["code"] == 30002
    # 旧 refresh 已吊销
    resp = await client.post("/api/v1/auth/refresh")
    assert resp.json()["code"] == 30002

    # 新密码登录成功，must_change_password 已清除
    resp = await client.post(
        "/api/v1/auth/login",
        json={"username": TEST_ADMIN_USERNAME, "password": NEW_PASSWORD},
    )
    assert resp.status_code == 200
    assert resp.json()["data"]["user"]["must_change_password"] is False


async def test_refresh_token_rotation(client: AsyncClient, fresh_admin) -> None:
    """刷新后旧 refresh 失效（轮换），新 refresh 可用。"""
    resp = await client.post(
        "/api/v1/auth/login",
        json={"username": TEST_ADMIN_USERNAME, "password": TEST_ADMIN_PASSWORD},
    )
    old_refresh = resp.cookies.get("refresh_token")
    assert old_refresh

    resp = await client.post("/api/v1/auth/refresh")
    assert resp.status_code == 200 and resp.json()["code"] == 0
    new_refresh = resp.cookies.get("refresh_token")
    assert new_refresh and new_refresh != old_refresh

    # 旧 refresh 已失效：清掉 cookie 后手写旧 token 模拟
    client.cookies.delete("refresh_token")
    client.cookies.set("refresh_token", old_refresh, path="/api/v1/auth")
    resp = await client.post("/api/v1/auth/refresh")
    assert resp.json()["code"] == 30002


async def test_logout_revokes_access_token(client: AsyncClient, fresh_admin) -> None:
    """登出后 access token 应被吊销（黑名单生效）。"""
    resp = await client.post(
        "/api/v1/auth/login",
        json={"username": TEST_ADMIN_USERNAME, "password": TEST_ADMIN_PASSWORD},
    )
    token = resp.json()["data"]["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    resp = await client.post("/api/v1/auth/logout", headers=headers)
    assert resp.status_code == 200 and resp.json()["code"] == 0

    resp = await client.get("/api/v1/auth/me", headers=headers)
    assert resp.json()["code"] == 30002


async def test_me_requires_auth(client: AsyncClient) -> None:
    """未携带 token 访问 /auth/me 返回 30000。"""
    resp = await client.get("/api/v1/auth/me")
    assert resp.json()["code"] == 30000