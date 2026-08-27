"""Repository 基类（《02-总体架构设计》第 2 节）。

Repository 只做数据访问，不包含业务规则；事务由 Service 层控制。
"""
from typing import Any, Generic, TypeVar

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.base import Base

ModelT = TypeVar("ModelT", bound=Base)


class BaseRepository(Generic[ModelT]):
    """通用数据访问基类。"""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get(self, model_cls: type[ModelT], entity_id: int) -> ModelT | None:
        """按主键查询。"""
        return await self._session.get(model_cls, entity_id)

    async def add(self, entity: ModelT) -> ModelT:
        """新增实体（不提交，由 Service 统一提交）。"""
        self._session.add(entity)
        await self._session.flush()
        return entity

    async def list_all(self, model_cls: type[ModelT]) -> list[ModelT]:
        """查询全部（不含软删除过滤，由具体 Repository 覆盖）。"""
        result = await self._session.execute(select(model_cls))
        return list(result.scalars().all())

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(session={id(self._session)})"