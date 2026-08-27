"""pytest 全局夹具与测试环境（《07-工程规范》第 6 节）。

重要安全约束：
- 当前数据库账号无 CREATEDB/独立测试库，pytest 会清空并重建 `contract_risk`
  库中的业务表（TRUNCATE）；
- 因此必须在运行测试前显式设置 `ALLOW_DESTRUCTIVE_TEST_DB=1`，否则直接拒绝启动，
  防止误清开发/生产数据。
- Redis：使用独立 db（REDIS_URL 指向 db=2），测试前后清空；
- 初始超管：使用专用测试账号 test_admin，避免污染真实超管。
"""
import os
from pathlib import Path

# 必须在导入 app 之前设置测试环境变量（settings 首次加载时生效）
if os.environ.get("ALLOW_DESTRUCTIVE_TEST_DB") != "1":
    raise RuntimeError(
        "Refusing to run tests: pytest will TRUNCATE the shared contract_risk DB. "
        "Set ALLOW_DESTRUCTIVE_TEST_DB=1 only if you explicitly want this."
    )


def _test_redis_url() -> str:
    """从 backend/.env 读取 Redis 连接并切到独立 db=2（测试隔离；不硬编码密码）。"""
    env_path = Path(__file__).resolve().parent.parent / ".env"
    vals: dict[str, str] = {}
    if env_path.exists():
        for line in env_path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, value = line.partition("=")
            vals[key.strip()] = value.strip().strip('"').strip("'")
    if vals.get("REDIS_URL"):
        base, _, _db = vals["REDIS_URL"].rpartition("/")
        return f"{base}/2"
    host = vals.get("REDIS_HOST", "127.0.0.1")
    port = vals.get("REDIS_PORT", "6379")
    password = vals.get("REDIS_PASSWORD", "")
    auth = f":{password}@" if password else ""
    return f"redis://{auth}{host}:{port}/2"


os.environ["REDIS_URL"] = _test_redis_url()
os.environ["ADMIN_USERNAME"] = "test_admin"
os.environ["ADMIN_PASSWORD"] = "Test@123456"
os.environ["FERNET_KEY"] = "test-fernet-key-0123456789abcdef"
os.environ["JWT_SECRET"] = "test-jwt-secret-0123456789abcdef0123456789"
os.environ["APP_ENV"] = "test"

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text

from app.core.database import SessionFactory
from app.integrations import redis_client
from app.main import app
from app.services.bootstrap import bootstrap

BASE_URL = "http://testserver"

TEST_ADMIN_USERNAME = os.environ["ADMIN_USERNAME"]
TEST_ADMIN_PASSWORD = os.environ["ADMIN_PASSWORD"]

_RESET_SQL = """
TRUNCATE TABLE sys_operation_log, sys_login_log, sys_user_identity,
    sys_user_role, sys_role_permission, sys_user, sys_config, sys_role,
    sys_permission RESTART IDENTITY CASCADE;
"""


async def _reset_all() -> None:
    """清空业务表并清空测试 Redis（保证可重复运行）。"""
    async with SessionFactory() as session:
        await session.execute(text(_RESET_SQL))
        await session.commit()
    await redis_client.get_redis().flushdb()


@pytest.fixture(scope="session", autouse=True)
async def prepared_environment():
    """整个测试会话开始前重置环境并执行种子引导。"""
    await _reset_all()
    async with SessionFactory() as session:
        await bootstrap(session)
    yield


@pytest.fixture
async def client() -> AsyncClient:
    """基于 ASGITransport 的 API 测试客户端。"""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url=BASE_URL) as c:
        yield c


@pytest.fixture
async def fresh_admin():
    """每个测试前重置超管（密码/强制改密）与钉钉配置为空，并清空 Redis。"""
    from sqlalchemy import update

    from app.core.security import hash_password
    from app.models.config import SysConfig
    from app.models.user import User

    async with SessionFactory() as session:
        await session.execute(
            update(User)
            .where(User.username == TEST_ADMIN_USERNAME)
            .values(password_hash=hash_password(TEST_ADMIN_PASSWORD), must_change_password=True)
        )
        await session.execute(
            update(SysConfig)
            .where(SysConfig.config_key == "dingtalk")
            .values(
                config_value={
                    "client_id": "",
                    "client_secret_enc": "",
                    "corp_id": "",
                    "redirect_uri": "",
                    "enabled": False,
                    "updated_at": None,
                },
                version=1,
            )
        )
        await session.commit()
    await redis_client.get_redis().flushdb()
    yield


@pytest.fixture
async def admin_token(client: AsyncClient, fresh_admin) -> str:
    """返回测试超管的 access token（登录后已完成强制改密）。"""
    # 首次登录（must_change_password=true）
    resp = await client.post(
        "/api/v1/auth/login",
        json={"username": TEST_ADMIN_USERNAME, "password": TEST_ADMIN_PASSWORD},
    )
    assert resp.status_code == 200 and resp.json()["code"] == 0
    token = resp.json()["data"]["access_token"]
    # 强制改密
    resp = await client.post(
        "/api/v1/auth/change-password",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "old_password": TEST_ADMIN_PASSWORD,
            "new_password": "Test@12345678",
        },
    )
    assert resp.status_code == 200 and resp.json()["code"] == 0
    # 新密码重新登录
    resp = await client.post(
        "/api/v1/auth/login",
        json={"username": TEST_ADMIN_USERNAME, "password": "Test@12345678"},
    )
    assert resp.status_code == 200 and resp.json()["code"] == 0
    return resp.json()["data"]["access_token"]