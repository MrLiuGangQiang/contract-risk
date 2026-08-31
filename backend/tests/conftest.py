"""pytest 全局夹具与测试环境（《07-工程规范》第 6 节）。

硬性安全约束（不可绕过，违反即拒绝/跳过）：
1. 测试必须使用独立测试库：环境变量 `TEST_DATABASE_URL`；
2. 测试库不得与开发库（.env 的 DATABASE_URL）指向同一数据库；
3. 已删除 ALLOW_DESTRUCTIVE_TEST_DB 逃生门：任何情况下都不允许清空共享库；
4. Redis 使用独立 db（REDIS_URL 指向 db=2），与开发缓存隔离；
5. 初始超管使用专用测试账号 test_admin，避免污染真实超管。

运行策略：
- 纯函数单测（不依赖数据库/Redis）始终可运行；
- 集成测试（client / admin_token / fresh_admin）需要独立测试库：
  未设置 TEST_DATABASE_URL 时**明确跳过**这些测试并提示，绝不触碰共享开发库。

背景：曾因测试清空共享开发库导致生产数据丢失（2026-08-29），
自此测试隔离为强制要求，无豁免途径。
"""
import os
from pathlib import Path
from urllib.parse import urlparse

ENV_PATH = Path(__file__).resolve().parent.parent / ".env"


def _read_dotenv() -> dict[str, str]:
    """读取 backend/.env（不引入额外依赖）。"""
    vals: dict[str, str] = {}
    if ENV_PATH.exists():
        for line in ENV_PATH.read_text(encoding="utf-8-sig").splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, value = line.partition("=")
            vals[key.strip()] = value.strip().strip('"').strip("'")
    return vals


def _db_identity(url: str) -> tuple[str, int, str]:
    """提取连接串的 (host, port, dbname)，用于判断是否同一数据库。"""
    parsed = urlparse(url)
    return (parsed.hostname or "", parsed.port or 5432, (parsed.path or "").lstrip("/"))


def _same_database(a: str, b: str) -> bool:
    """判断两个连接串是否指向同一数据库。"""
    return _db_identity(a) == _db_identity(b)


def _resolve_test_database(dev_url: str) -> str | None:
    """解析并强校验测试库地址。

    返回可用的测试库连接串；不合规或未配置时返回 None（集成测试将被跳过）。
    """
    test_url = os.environ.get("TEST_DATABASE_URL", "").strip()
    if not test_url:
        return None
    if dev_url and _same_database(dev_url, test_url):
        # 致命：宁可全部跳过，也绝不允许测试写共享库
        raise RuntimeError(
            "TEST_DATABASE_URL 与开发库 DATABASE_URL 指向同一数据库，已拒绝运行。\n"
            "测试必须使用独立数据库（不同的库名），否则将摧毁开发/生产数据。"
        )
    return test_url


# ========== 在导入 app 之前确定环境变量（settings 首次加载时生效） ==========
_dotenv_vals = _read_dotenv()
_dev_db_url = _dotenv_vals.get("DATABASE_URL", "")

# 集成测试可用的独立测试库（未配置时为 None）
TEST_DB_URL = _resolve_test_database(_dev_db_url)
INTEGRATION_DB_AVAILABLE = TEST_DB_URL is not None

# 关键保护：绝不让 app 使用共享开发库跑测试。
# - 配置了独立测试库：使用该测试库；
# - 未配置：指向一个专用的"不可用测试库"地址（同服务器、不同库名）。
#   这样即便有测试误触发数据库连接，也只会连接失败/失败于测试库，
#   而永远不会连接到共享开发库 contract_risk。
if TEST_DB_URL is not None:
    os.environ["DATABASE_URL"] = TEST_DB_URL
else:
    if _dev_db_url:
        # 将开发库名后缀 _test，构造一个隔离占位地址（该库不存在，连接会失败——这是安全的）
        parsed = urlparse(_dev_db_url)
        dev_dbname = (parsed.path or "").lstrip("/")
        placeholder = _dev_db_url.replace(f"/{dev_dbname}", f"/{dev_dbname}_test", 1) if dev_dbname else _dev_db_url
        os.environ["DATABASE_URL"] = placeholder
    # 若 .env 没有 DATABASE_URL，保持未设置（settings 会因缺必填项报错，属预期）


def _test_redis_url() -> str:
    """从 backend/.env 读取 Redis 连接并切到独立 db=2（测试隔离；不硬编码密码）。"""
    vals = _dotenv_vals
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

_SKIP_NO_TEST_DB = (
    "跳过集成测试：未配置独立测试库。"
    "请设置 TEST_DATABASE_URL 指向专用测试库（如 .../contract_risk_test）后重跑。"
    "为保护共享开发库，绝不回退使用共享库。"
)

# 仅清空测试库中的业务表（_resolve_test_database 已强校验其为独立测试库）
_RESET_SQL = """
TRUNCATE TABLE sys_contract_risk, sys_contract, sys_risk_rule_custom,
    sys_risk_rule, sys_operation_log, sys_login_log, sys_user_identity,
    sys_user_role, sys_role_permission, sys_user, sys_config, sys_role,
    sys_permission RESTART IDENTITY CASCADE;
"""


async def _reset_all() -> None:
    """清空测试库业务表并清空测试 Redis（保证可重复运行；仅作用于独立测试库）。"""
    async with SessionFactory() as session:
        await session.execute(text(_RESET_SQL))
        await session.commit()
    await redis_client.get_redis().flushdb()


@pytest.fixture(scope="session", autouse=True)
async def prepared_environment():
    """会话级准备：仅在配置了独立测试库时执行重置与种子引导。

    未配置独立测试库时不做任何数据库操作（保护共享库），集成测试由各夹具跳过。
    """
    if INTEGRATION_DB_AVAILABLE:
        await _reset_all()
        async with SessionFactory() as session:
            await bootstrap(session)
    yield


@pytest.fixture
async def client() -> AsyncClient:
    """基于 ASGITransport 的 API 测试客户端（需要独立测试库）。"""
    if not INTEGRATION_DB_AVAILABLE:
        pytest.skip(_SKIP_NO_TEST_DB)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url=BASE_URL) as c:
        yield c


@pytest.fixture
async def fresh_admin():
    """每个测试前重置超管（密码/强制改密）与钉钉配置为空，并清空测试 Redis。"""
    if not INTEGRATION_DB_AVAILABLE:
        pytest.skip(_SKIP_NO_TEST_DB)
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
