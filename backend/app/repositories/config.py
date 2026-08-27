"""系统配置数据访问（ConfigRepository）。"""
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.config import SysConfig
from app.repositories.base import BaseRepository


class ConfigRepository(BaseRepository[SysConfig]):
    """sys_config 数据访问。"""

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session)

    async def get_by_key(self, config_key: str) -> SysConfig | None:
        """按配置键查询。"""
        stmt = select(SysConfig).where(SysConfig.config_key == config_key)
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def upsert(
        self,
        *,
        config_key: str,
        config_value: dict[str, Any],
        is_encrypted: bool,
        description: str | None,
        updated_by: int,
    ) -> SysConfig:
        """新增或更新配置（乐观锁由 Service 层处理 version 冲突）。"""
        entity = await self.get_by_key(config_key)
        if entity is None:
            entity = SysConfig(
                config_key=config_key,
                config_value=config_value,
                value_type="json",
                is_encrypted=is_encrypted,
                description=description,
                version=1,
                updated_by=updated_by,
            )
            self._session.add(entity)
        else:
            entity.config_value = config_value
            entity.is_encrypted = is_encrypted
            entity.description = description
            entity.updated_by = updated_by
            entity.version += 1
        await self._session.flush()
        return entity