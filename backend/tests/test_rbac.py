"""RBAC 测试：普通用户（钉钉/本地）访问超管配置接口统一返回 404（完全隐藏，《04》第 4.3 节）。"""

from httpx import AsyncClient

from app.core.database import SessionFactory
from app.core.security import hash_password
from app.domain.constants import ROLE_USER
from app.models.user import Role, User, UserRole


async def _create_local_user(username: str, password: str) -> None:
    """创建一个带本地密码的普通用户（测试辅助）。"""
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
        role = (await session.execute(__import__("sqlalchemy").select(Role).where(Role.code == ROLE_USER))).scalar_one()
        session.add(UserRole(user_id=user.id, role_id=role.id))
        await session.commit()


async def test_normal_user_cannot_access_config(
    client: AsyncClient, fresh_admin
) -> None:
    """普通用户登录后可访问 /auth/me，但访问钉钉配置接口统一返回 404（与不存在路由一致）。"""
    await _create_local_user("normal_user", "Normal@123456")
    resp = await client.post(
        "/api/v1/auth/login",
        json={"username": "normal_user", "password": "Normal@123456"},
    )
    assert resp.json()["code"] == 0
    token = resp.json()["data"]["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # 可访问自己的信息
    resp = await client.get("/api/v1/auth/me", headers=headers)
    assert resp.json()["code"] == 0
    assert resp.json()["data"]["is_super_admin"] is False

    # 隐藏语义：无权读/写/测试配置统一返回 404，与不存在路由一致
    resp = await client.get("/api/v1/admin/configs/dingtalk", headers=headers)
    assert resp.status_code == 404
    assert resp.json()["code"] == 10001
    resp = await client.put(
        "/api/v1/admin/configs/dingtalk",
        headers=headers,
        json={"client_id": "x", "redirect_uri": "http://x", "enabled": False},
    )
    assert resp.status_code == 404
    assert resp.json()["code"] == 10001
    resp = await client.post("/api/v1/admin/configs/dingtalk/test", headers=headers)
    assert resp.status_code == 404
    assert resp.json()["code"] == 10001
