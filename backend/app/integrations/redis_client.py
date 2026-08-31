"""Redis 客户端与键管理（《03-数据模型设计》第 5 节）。

- 统一封装连接与键前缀，禁止业务代码散落 Redis 键字符串；
- 会话/限流/OAuth state/配置缓存均通过本模块访问。
"""
import json
from typing import Any

import redis.asyncio as aioredis

from app.core.config import get_settings
from app.domain.constants import (
    REDIS_BLACKLIST_PREFIX,
    REDIS_CONFIG_CACHE_PREFIX,
    REDIS_DINGTALK_STATE_PREFIX,
    REDIS_RATELIMIT_LOGIN_FAIL_PREFIX,
    REDIS_RATELIMIT_LOGIN_PREFIX,
    REDIS_REFRESH_PREFIX,
)

_pool: aioredis.Redis | None = None


def get_redis() -> aioredis.Redis:
    """返回 Redis 客户端单例（惰性初始化，连接池复用）。"""
    global _pool
    if _pool is None:
        settings = get_settings()
        _pool = aioredis.from_url(
            settings.redis_url,
            encoding="utf-8",
            decode_responses=True,
            max_connections=settings.redis_max_connections,
            # 远端 Redis 会回收空闲连接：主动健康检查 + TCP keepalive，
            # 避免取出陈旧连接时才收到 10054 强制断开
            health_check_interval=30,
            socket_keepalive=True,
        )
    return _pool


async def close_redis() -> None:
    """关闭 Redis 连接池（应用退出时调用）。"""
    global _pool
    if _pool is not None:
        await _pool.aclose()
        _pool = None


# ==================== 键构造 ====================

def _refresh_key(user_id: int, jti: str) -> str:
    return f"{REDIS_REFRESH_PREFIX}{user_id}:{jti}"


def _refresh_user_key(user_id: int) -> str:
    """用户维度 refresh 集合键（用于改密后吊销全部旧令牌）。"""
    return f"{REDIS_REFRESH_PREFIX}user:{user_id}"


def _blacklist_key(jti: str) -> str:
    return f"{REDIS_BLACKLIST_PREFIX}{jti}"


def _dingtalk_state_key(state: str) -> str:
    return f"{REDIS_DINGTALK_STATE_PREFIX}{state}"


def _login_rate_key(identifier: str) -> str:
    return f"{REDIS_RATELIMIT_LOGIN_PREFIX}{identifier}"


def _login_fail_key(identifier: str) -> str:
    return f"{REDIS_RATELIMIT_LOGIN_FAIL_PREFIX}{identifier}"


def _login_fail_lock_key(identifier: str) -> str:
    """连续失败达到阈值后的锁定标记键（与计数键分离，避免 1 次失败即被误判为锁定）。"""
    return f"{REDIS_RATELIMIT_LOGIN_FAIL_PREFIX}lock:{identifier}"


def _config_cache_key(config_key: str) -> str:
    return f"{REDIS_CONFIG_CACHE_PREFIX}{config_key}"


# ==================== 令牌 ====================

async def save_refresh_token(user_id: int, jti: str, ttl_seconds: int) -> None:
    """记录 refresh token（用于轮换/吊销），并加入用户维度集合。"""
    await get_redis().set(_refresh_key(user_id, jti), "1", ex=ttl_seconds)
    await get_redis().sadd(_refresh_user_key(user_id), jti)


async def revoke_refresh_token(user_id: int, jti: str) -> None:
    """吊销指定 refresh token。"""
    await get_redis().delete(_refresh_key(user_id, jti))
    await get_redis().srem(_refresh_user_key(user_id), jti)


async def revoke_all_refresh_tokens(user_id: int) -> None:
    """吊销用户全部 refresh token（改密/禁用时调用）。"""
    jtis = await get_redis().smembers(_refresh_user_key(user_id))
    for jti in jtis:
        await get_redis().delete(_refresh_key(user_id, jti))
    if jtis:
        await get_redis().delete(_refresh_user_key(user_id))


async def refresh_token_exists(user_id: int, jti: str) -> bool:
    """判断 refresh token 是否仍有效。"""
    return await get_redis().exists(_refresh_key(user_id, jti)) > 0


async def blacklist_access_token(jti: str, ttl_seconds: int) -> None:
    """将 access token 加入黑名单（登出/改密时调用）。"""
    await get_redis().set(_blacklist_key(jti), "1", ex=ttl_seconds)


async def is_access_token_blacklisted(jti: str) -> bool:
    """判断 access token 是否已被吊销。"""
    return await get_redis().exists(_blacklist_key(jti)) > 0


# ==================== 钉钉 OAuth state ====================

async def save_dingtalk_state(state: str, ttl_seconds: int) -> None:
    """保存 OAuth state（防 CSRF，一次性）。"""
    await get_redis().set(_dingtalk_state_key(state), "1", ex=ttl_seconds)


async def consume_dingtalk_state(state: str) -> bool:
    """校验并消费 state（存在则删除，返回是否有效）。"""
    key = _dingtalk_state_key(state)
    existed = await get_redis().exists(key) > 0
    if existed:
        await get_redis().delete(key)
    return existed


# ==================== 登录限流 ====================

async def login_rate_exceeded(identifier: str, limit_per_minute: int) -> bool:
    """按 IP/账号维度限流：每分钟超过 limit 则拒绝。"""
    key = _login_rate_key(identifier)
    pipe = get_redis().pipeline()
    pipe.incr(key)
    pipe.expire(key, 60)
    count, _ = await pipe.execute()
    return int(count) > limit_per_minute


async def login_fail_locked(identifier: str, max_fails: int, lock_minutes: int) -> bool:
    """连续失败锁定：仅当锁定标记存在时返回 True。

    计数键（失败次数）与锁定键分离：失败 1~(max_fails-1) 次只累计计数，
    达到 max_fails 次才写入锁定标记（锁定 lock_minutes 分钟）。
    """
    return bool(await get_redis().get(_login_fail_lock_key(identifier)))


async def record_login_fail(identifier: str, max_fails: int, lock_minutes: int) -> None:
    """记录一次登录失败，达到阈值后写入锁定标记。"""
    key = _login_fail_key(identifier)
    count = await get_redis().incr(key)
    if count == 1:
        await get_redis().expire(key, 60 * 60)  # 计数窗口 1 小时
    if int(count) >= max_fails:
        await get_redis().set(_login_fail_lock_key(identifier), "1", ex=lock_minutes * 60)
        await get_redis().delete(key)  # 锁定后清零计数，解锁后重新累计


async def clear_login_fail(identifier: str) -> None:
    """登录成功后清除失败计数（不影响锁定标记，锁定需等待到期）。"""
    await get_redis().delete(_login_fail_key(identifier))


# ==================== 配置缓存 ====================

async def get_cached_config(config_key: str) -> dict[str, Any] | None:
    """读取配置缓存（不存在返回 None）。"""
    raw = await get_redis().get(_config_cache_key(config_key))
    if raw is None:
        return None
    try:
        return json.loads(raw)
    except (TypeError, ValueError):
        return None


async def cache_config(config_key: str, value: dict[str, Any], ttl_seconds: int = 300) -> None:
    """写入配置缓存（默认 5 分钟）。"""
    await get_redis().set(_config_cache_key(config_key), json.dumps(value, ensure_ascii=False), ex=ttl_seconds)


async def invalidate_config_cache(config_key: str) -> None:
    """删除配置缓存（配置变更时调用）。"""
    await get_redis().delete(_config_cache_key(config_key))