"""风险规则数据访问（《10-合同风险规则配置设计》第 2 节）。

Repository 只做数据访问，业务规则与事务由 Service 控制。
"""
from sqlalchemy import delete, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.risk_rule import RiskRule, RiskRuleCustom


class RiskRuleRepository:
    """风险规则 Repository。"""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def list_rules(
        self,
        *,
        page: int,
        page_size: int,
        keyword: str | None,
        category: str | None,
        severity: str | None,
        enabled: bool | None,
    ) -> tuple[list[RiskRule], int]:
        """分页查询（不含软删除），支持关键词/分类/级别/启用状态过滤。"""
        stmt = select(RiskRule).where(RiskRule.deleted_at.is_(None))
        count_stmt = select(func.count()).select_from(RiskRule).where(RiskRule.deleted_at.is_(None))
        if keyword:
            like = f"%{keyword}%"
            stmt = stmt.where(or_(RiskRule.code.ilike(like), RiskRule.name.ilike(like)))
            count_stmt = count_stmt.where(or_(RiskRule.code.ilike(like), RiskRule.name.ilike(like)))
        if category:
            stmt = stmt.where(RiskRule.category == category)
            count_stmt = count_stmt.where(RiskRule.category == category)
        if severity:
            stmt = stmt.where(RiskRule.severity == severity)
            count_stmt = count_stmt.where(RiskRule.severity == severity)
        if enabled is not None:
            stmt = stmt.where(RiskRule.enabled == enabled)
            count_stmt = count_stmt.where(RiskRule.enabled == enabled)

        total = int((await self._session.execute(count_stmt)).scalar_one())
        stmt = stmt.order_by(RiskRule.sort_order, RiskRule.id).offset((page - 1) * page_size).limit(page_size)
        result = await self._session.execute(stmt)
        return list(result.scalars().all()), total

    async def get_by_code(self, code: str) -> RiskRule | None:
        """按编码查询未删除规则。"""
        stmt = select(RiskRule).where(
            RiskRule.code == code, RiskRule.deleted_at.is_(None)
        )
        return (await self._session.execute(stmt)).scalar_one_or_none()

    async def get_by_id(self, rule_id: int) -> RiskRule | None:
        """按主键查询未删除规则。"""
        stmt = select(RiskRule).where(
            RiskRule.id == rule_id, RiskRule.deleted_at.is_(None)
        )
        return (await self._session.execute(stmt)).scalar_one_or_none()

    async def list_export(self) -> list[RiskRule]:
        """导出全部未删除规则（按排序）。"""
        stmt = (
            select(RiskRule)
            .where(RiskRule.deleted_at.is_(None))
            .order_by(RiskRule.sort_order, RiskRule.id)
        )
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def add(self, rule: RiskRule) -> RiskRule:
        """新增规则（不提交，由 Service 提交）。"""
        self._session.add(rule)
        await self._session.flush()
        return rule



class RiskRuleCustomRepository:
    """个人风险规则副本 Repository。"""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def list_by_user(self, user_id: int) -> list[RiskRuleCustom]:
        """查询用户全部个人副本。"""
        stmt = select(RiskRuleCustom).where(RiskRuleCustom.user_id == user_id).order_by(
            RiskRuleCustom.sort_order, RiskRuleCustom.id
        )
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def get_by_user_code(self, user_id: int, code: str) -> RiskRuleCustom | None:
        """按用户+编码查询个人副本。"""
        stmt = select(RiskRuleCustom).where(
            RiskRuleCustom.user_id == user_id, RiskRuleCustom.code == code
        )
        return (await self._session.execute(stmt)).scalar_one_or_none()

    async def add(self, entity: RiskRuleCustom) -> RiskRuleCustom:
        """新增个人副本。"""
        self._session.add(entity)
        await self._session.flush()
        return entity

    async def delete_by_user_code(self, user_id: int, code: str) -> None:
        """删除单条个人副本（恢复单条默认）。"""
        await self._session.execute(
            delete(RiskRuleCustom).where(
                RiskRuleCustom.user_id == user_id, RiskRuleCustom.code == code
            )
        )
        await self._session.flush()

    async def delete_all_by_user(self, user_id: int) -> None:
        """删除用户全部个人副本（一键恢复默认）。"""
        await self._session.execute(
            delete(RiskRuleCustom).where(RiskRuleCustom.user_id == user_id)
        )
        await self._session.flush()
