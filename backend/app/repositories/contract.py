"""合同与风险结果数据访问（《11-合同风险识别核心功能设计》）。

Repository 只做数据访问；文件解析、规则匹配与事务由 Service 控制。
"""
from sqlalchemy import delete, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.contract import Contract, ContractRisk


class ContractRepository:
    """合同 Repository。"""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def list_contracts(
        self,
        *,
        user_id: int,
        page: int,
        page_size: int,
        keyword: str | None,
        severity: str | None,
    ) -> tuple[list[Contract], int]:
        """分页查询当前用户合同（支持文件名搜索、按风险级别过滤）。"""
        stmt = select(Contract).where(Contract.user_id == user_id, Contract.deleted_at.is_(None))
        count_stmt = select(func.count()).select_from(Contract).where(
            Contract.user_id == user_id, Contract.deleted_at.is_(None)
        )
        if keyword:
            like = f"%{keyword}%"
            stmt = stmt.where(Contract.file_name.ilike(like))
            count_stmt = count_stmt.where(Contract.file_name.ilike(like))
        if severity:
            contract_ids = (
                select(ContractRisk.contract_id)
                .where(ContractRisk.user_id == user_id, ContractRisk.severity == severity)
                .distinct()
            )
            stmt = stmt.where(Contract.id.in_(contract_ids))
            count_stmt = count_stmt.where(Contract.id.in_(contract_ids))
        total = int((await self._session.execute(count_stmt)).scalar_one())
        stmt = stmt.order_by(Contract.created_at.desc(), Contract.id.desc()).offset(
            (page - 1) * page_size
        ).limit(page_size)
        result = await self._session.execute(stmt)
        return list(result.scalars().all()), total

    async def get_contract(self, user_id: int, contract_id: int) -> Contract | None:
        """按用户+合同号查询（未删除）。"""
        stmt = select(Contract).where(
            Contract.user_id == user_id,
            Contract.id == contract_id,
            Contract.deleted_at.is_(None),
        )
        return (await self._session.execute(stmt)).scalar_one_or_none()

    async def list_risks(self, contract_id: int) -> list[ContractRisk]:
        """查询合同风险结果。"""
        stmt = (
            select(ContractRisk)
            .where(ContractRisk.contract_id == contract_id)
            .order_by(ContractRisk.sort_order, ContractRisk.id)
        )
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def add_contract(self, contract: Contract) -> Contract:
        """新增合同。"""
        self._session.add(contract)
        await self._session.flush()
        return contract

    async def replace_risks(self, contract_id: int, user_id: int, risks: list[ContractRisk]) -> None:
        """原子替换风险结果（先删后插，调用方事务控制）。"""
        await self._session.execute(
            delete(ContractRisk).where(ContractRisk.contract_id == contract_id)
        )
        for risk in risks:
            self._session.add(risk)
        await self._session.flush()

    async def soft_delete_contract(self, contract: Contract) -> None:
        """软删除合同并删除风险结果。"""
        from datetime import datetime, timezone

        contract.deleted_at = datetime.now(timezone.utc)
        await self._session.execute(
            delete(ContractRisk).where(ContractRisk.contract_id == contract.id)
        )
        await self._session.flush()