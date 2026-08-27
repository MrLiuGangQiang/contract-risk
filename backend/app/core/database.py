"""数据库引擎与会话管理（SQLAlchemy 2.0 async + asyncpg）。

- 连接池参数由环境变量配置（DB_POOL_*，见《02》4.6 与《09》第 2 节），
  默认 pool_size=10 / max_overflow=20，按 worker 数 × 10~20 调整。
- 事务边界由 Service 层控制（Unit of Work），Repository 不开启事务。
遵循《02-总体架构设计》第 4.4 节。
"""
from collections.abc import AsyncIterator

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.core.config import get_settings

_settings = get_settings()

_engine = create_async_engine(
    _settings.get_database_url(),
    echo=_settings.db_echo,
    pool_size=_settings.db_pool_size,
    max_overflow=_settings.db_max_overflow,
    pool_timeout=_settings.db_pool_timeout,
    pool_recycle=_settings.db_pool_recycle,
    pool_pre_ping=_settings.db_pool_pre_ping,
)

SessionFactory = async_sessionmaker(_engine, class_=AsyncSession, expire_on_commit=False)


async def get_db() -> AsyncIterator[AsyncSession]:
    """FastAPI 依赖：提供请求级数据库会话。"""
    async with SessionFactory() as session:
        yield session