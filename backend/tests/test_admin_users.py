"""超管用户与角色管理测试（《04》4.4、《05》2.4 节）。
覆盖：普通用户 404 隐藏、超管列表/创建/更新/重置/删除、
保护自己、登录方式探测。
"""
from httpx import AsyncClient

from app.core.database import SessionFactory
from app.core.security import hash_password
from app.domain.constants import ROLE_USER
from app.models.user import Role, User, UserRole


async def _create_local_user(username: str, password: str) -> None:
    """创建带本地密码的普通用户（测试辅助）。"""
    async with SessionFactory() as session:
        user = User(
            username=username,
            password_hash=hash_password(password),
            display_name="普通用户",
            status=1,
            is_super_admin=False,
            must_change_password=False,
        )
        session.add(user)
        await session.flush()
        role = (
            await session.execute(__import__("sqlalchemy").select(Role).where(Role.code == ROLE_USER))
        ).scalar_one()
        session.add(UserRole(user_id=user.id, role_id=role.id))
        await session.commit()


async def _login(client: AsyncClient, username: str, password: str) -> str:
    """登录并返回 access token。"""
    resp = await client.post("/api/v1/auth/login", json={"username": username, "password": password})
    assert resp.status_code == 200 and resp.json()["code"] == 0
    return resp.json()["data"]["access_token"]


async def test_normal_user_gets_404_on_user_management(client: AsyncClient, fresh_admin) -> None:
    """普通用户访问用户/角色管理接口统一 404（隐藏）。"""
    await _create_local_user("normal_user", "Normal@123456")
    token = await _login(client, "normal_user", "Normal@123456")
    headers = {"Authorization": f"Bearer {token}"}

    checks = [
        ("GET", "/api/v1/admin/users", None),
        ("POST", "/api/v1/admin/users", {"username": "x", "display_name": "x", "password": "Xx@12345678", "roles": ["user"]}),
        ("GET", "/api/v1/admin/roles", None),
    ]
    for method, path, body in checks:
        resp = await client.request(method, path, headers=headers, json=body)
        assert resp.status_code == 404
        assert resp.json()["code"] == 10001


async def test_admin_creates_updates_resets_deletes_user(
    client: AsyncClient, fresh_admin, admin_token
) -> None:
    """超管列表/创建/更新角色/重置密码/删除用户全流程。"""
    headers = {"Authorization": f"Bearer {admin_token}"}

    resp = await client.get("/api/v1/admin/roles", headers=headers)
    assert resp.status_code == 200 and resp.json()["code"] == 0
    roles = resp.json()["data"]
    assert any(r["code"] == "user" for r in roles)

    resp = await client.post(
        "/api/v1/admin/users",
        headers=headers,
        json={"username": "zhangsan", "display_name": "张三", "password": "Zhang@123456", "roles": ["user"]},
    )
    assert resp.status_code == 200 and resp.json()["code"] == 0
    user = resp.json()["data"]
    assert user["username"] == "zhangsan"
    assert user["must_change_password"] is True
    assert [r["code"] for r in user["roles"]] == ["user"]
    user_id = user["id"]

    resp = await client.put(
        f"/api/v1/admin/users/{user_id}",
        headers=headers,
        json={"display_name": "张三丰", "status": 0, "roles": ["user"]},
    )
    assert resp.status_code == 200 and resp.json()["code"] == 0
    assert resp.json()["data"]["status"] == 0

    resp = await client.put(
        f"/api/v1/admin/users/{user_id}/password",
        headers=headers,
        json={"password": "New@12345678"},
    )
    assert resp.status_code == 200 and resp.json()["code"] == 0

    resp = await client.get("/api/v1/admin/users", headers=headers, params={"keyword": "zhangsan"})
    assert resp.status_code == 200 and resp.json()["code"] == 0
    assert resp.json()["data"]["total"] >= 1

    resp = await client.delete(f"/api/v1/admin/users/{user_id}", headers=headers)
    assert resp.status_code == 200 and resp.json()["code"] == 0


async def test_admin_cannot_delete_self(client: AsyncClient, fresh_admin, admin_token) -> None:
    """禁止删除自己。"""
    headers = {"Authorization": f"Bearer {admin_token}"}
    me = await client.get("/api/v1/auth/me", headers=headers)
    my_id = me.json()["data"]["id"]
    resp = await client.delete(f"/api/v1/admin/users/{my_id}", headers=headers)
    assert resp.status_code == 200
    assert resp.json()["code"] == 40000


async def test_login_methods_reflects_dingtalk_enabled(
    client: AsyncClient, fresh_admin, admin_token
) -> None:
    """登录方式探测：未启用 false，启用后 true。"""
    resp = await client.get("/api/v1/auth/login-methods")
    assert resp.status_code == 200 and resp.json()["code"] == 0
    assert resp.json()["data"]["dingtalk_enabled"] is False

    headers = {"Authorization": f"Bearer {admin_token}"}
    resp = await client.put(
        "/api/v1/admin/configs/dingtalk",
        headers=headers,
        json={"client_id": "dingtest", "client_secret": "", "corp_id": "dingcorp", "redirect_uri": "http://localhost:5173/dingtalk/callback", "enabled": True},
    )
    assert resp.status_code == 200 and resp.json()["code"] == 0

    resp = await client.get("/api/v1/auth/login-methods")
    assert resp.status_code == 200 and resp.json()["code"] == 0
    assert resp.json()["data"]["dingtalk_enabled"] is True
