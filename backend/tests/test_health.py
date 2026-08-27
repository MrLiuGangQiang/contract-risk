"""健康检查测试（/api/v1/health）。"""

from httpx import AsyncClient


async def test_health_returns_ok(client: AsyncClient) -> None:
    """健康检查应返回服务/数据库/Redis 均正常。"""
    resp = await client.get("/api/v1/health")
    assert resp.status_code == 200
    body = resp.json()
    assert body["code"] == 0
    assert body["data"]["service"] == "ok"
    assert body["data"]["database"] == "ok"
    assert body["data"]["redis"] == "ok"
    assert body["request_id"]