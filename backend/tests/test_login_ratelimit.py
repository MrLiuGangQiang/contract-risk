"""登录失败锁定机制回归测试（防止 1 次失败即锁定的缺陷复现）。

背景：曾存在缺陷——失败计数键与锁定标记键为同一键，
`login_fail_locked` 把计数 "1" 也判定为锁定，导致错 1 次就提示「账号已临时锁定」。

本测试直接验证 redis_client 的计数/锁定语义（使用测试 Redis db=2，与开发缓存隔离）。
"""
import pytest

from app.integrations import redis_client

LOCK_ID = "test_lock_identifier"
MAX_FAILS = 5
LOCK_MINUTES = 15


@pytest.fixture(autouse=True)
async def clean_keys():
    """每个用例前后清理测试键。"""
    client = await redis_client.get_redis()
    for suffix in ("", "lock:"):
        await client.delete(f"ratelimit:login_fail:{suffix}{LOCK_ID}")
    yield
    for suffix in ("", "lock:"):
        await client.delete(f"ratelimit:login_fail:{suffix}{LOCK_ID}")


async def test_single_failure_does_not_lock() -> None:
    """失败 1 次不得锁定（回归核心）。"""
    await redis_client.record_login_fail(LOCK_ID, MAX_FAILS, LOCK_MINUTES)
    assert await redis_client.login_fail_locked(LOCK_ID, MAX_FAILS, LOCK_MINUTES) is False


async def test_below_threshold_does_not_lock() -> None:
    """失败 4 次（阈值 5）仍不得锁定。"""
    for _ in range(MAX_FAILS - 1):
        await redis_client.record_login_fail(LOCK_ID, MAX_FAILS, LOCK_MINUTES)
    assert await redis_client.login_fail_locked(LOCK_ID, MAX_FAILS, LOCK_MINUTES) is False


async def test_threshold_locks() -> None:
    """失败达到阈值（5 次）才锁定。"""
    for _ in range(MAX_FAILS):
        await redis_client.record_login_fail(LOCK_ID, MAX_FAILS, LOCK_MINUTES)
    assert await redis_client.login_fail_locked(LOCK_ID, MAX_FAILS, LOCK_MINUTES) is True


async def test_clear_failure_count_not_lock() -> None:
    """登录成功清除失败计数，不影响锁定标记。"""
    await redis_client.record_login_fail(LOCK_ID, MAX_FAILS, LOCK_MINUTES)
    await redis_client.clear_login_fail(LOCK_ID)
    assert await redis_client.login_fail_locked(LOCK_ID, MAX_FAILS, LOCK_MINUTES) is False
    # 再次失败从 1 重新计数，仍不锁定
    await redis_client.record_login_fail(LOCK_ID, MAX_FAILS, LOCK_MINUTES)
    assert await redis_client.login_fail_locked(LOCK_ID, MAX_FAILS, LOCK_MINUTES) is False
