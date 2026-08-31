"""风险规则数据访问（《10-合同风险规则配置设计》，极简模型）。"""
from datetime import datetime, timezone

from sqlalchemy import delete, func, or_, select, update
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
        enabled: bool | None,
    ) -> tuple[list[RiskRule], int]:
        """分页查询（不含软删除），支持关键词/维度/启用状态过滤。"""
        stmt = select(RiskRule).where(RiskRule.deleted_at.is_(None))
        count_stmt = select(func.count()).select_from(RiskRule).where(RiskRule.deleted_at.is_(None))
        if keyword:
            like = f"%{keyword}%"
            stmt = stmt.where(RiskRule.rule_text.ilike(like))
            count_stmt = count_stmt.where(RiskRule.rule_text.ilike(like))
        if category:
            stmt = stmt.where(RiskRule.category == category)
            count_stmt = count_stmt.where(RiskRule.category == category)
        if enabled is not None:
            stmt = stmt.where(RiskRule.enabled == enabled)
            count_stmt = count_stmt.where(RiskRule.enabled == enabled)

        total = int((await self._session.execute(count_stmt)).scalar_one())
        stmt = stmt.order_by(RiskRule.sort_order, RiskRule.id).offset((page - 1) * page_size).limit(page_size)
        result = await self._session.execute(stmt)
        return list(result.scalars().all()), total

    async def get_by_id(self, rule_id: int) -> RiskRule | None:
        """按主键查询未删除规则。"""
        stmt = select(RiskRule).where(RiskRule.id == rule_id, RiskRule.deleted_at.is_(None))
        return (await self._session.execute(stmt)).scalar_one_or_none()

    async def get_by_rule_text(self, rule_text: str) -> RiskRule | None:
        """按一句话规则原文精确匹配未删除规则（幂等导入/去重）。"""
        stmt = (
            select(RiskRule)
            .where(RiskRule.rule_text == rule_text, RiskRule.deleted_at.is_(None))
            .order_by(RiskRule.id)
            .limit(1)
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

    async def soft_delete(self, rule: RiskRule) -> None:
        """软删除规则。"""
        rule.deleted_at = datetime.now(timezone.utc)
        await self._session.flush()


class RiskRuleCustomRepository:
    """个人风险规则副本 Repository。"""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def list_by_user(self, user_id: int) -> list[RiskRuleCustom]:
        """查询用户全部个人副本。"""
        stmt = (
            select(RiskRuleCustom)
            .where(RiskRuleCustom.user_id == user_id)
            .order_by(RiskRuleCustom.sort_order, RiskRuleCustom.id)
        )
        return list((await self._session.execute(stmt)).scalars().all())

    async def get_by_user_rule(self, user_id: int, rule_id: int) -> RiskRuleCustom | None:
        """按用户+全局规则 id 查询个人副本。"""
        stmt = select(RiskRuleCustom).where(
            RiskRuleCustom.user_id == user_id, RiskRuleCustom.rule_id == rule_id
        )
        return (await self._session.execute(stmt)).scalar_one_or_none()

    async def delete_by_user_rule(self, user_id: int, rule_id: int) -> None:
        """删除单条个人副本（恢复单条默认）。"""
        await self._session.execute(
            delete(RiskRuleCustom).where(
                RiskRuleCustom.user_id == user_id, RiskRuleCustom.rule_id == rule_id
            )
        )
        await self._session.flush()

    async def delete_all_by_user(self, user_id: int) -> None:
        """删除用户全部个人副本（一键恢复默认）。"""
        await self._session.execute(delete(RiskRuleCustom).where(RiskRuleCustom.user_id == user_id))
        await self._session.flush()
