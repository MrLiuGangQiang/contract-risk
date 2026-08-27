"""数据库引擎与会话管理（SQLAlchemy 2.0 async + asyncpg）。

- 连接池：pool_size=10 / max_overflow=20（按 worker 数 × 10~20 调整）。
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

_engine = create_async_engine(
    get_settings().database_url,
    echo=False,
    pool_size=10,
    max_overflow=20,
    pool_pre_ping=True,
)

SessionFactory = async_sessionmaker(_engine, class_=AsyncSession, expire_on_commit=False)


async def get_db() -> AsyncIterator[AsyncSession]:
    """FastAPI 依赖：提供请求级数据库会话。"""
    async with SessionFactory() as session:
        yield session