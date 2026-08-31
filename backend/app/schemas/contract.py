"""合同风险识别 DTO（《11-合同风险识别核心功能设计》第 5 节）。"""
from datetime import datetime

from pydantic import BaseModel, Field


class ContractRiskOut(BaseModel):
    """风险结果响应（含规则快照）。"""

    id: int
    rule_code: str | None = None
    snippet_start: int | None = None
    snippet_end: int | None = None
    rule_name: str
    category: str
    severity: str
    matched_keywords: list[str] = Field(default_factory=list)
    risk_source: str = "rule"
    snippet: str
    description: str
    suggestion: str
    sort_order: int
    created_at: datetime | None = None


class ContractOut(BaseModel):
    """合同列表/详情响应。"""

    id: int
    user_id: int
    file_name: str
    file_ext: str
    file_size: int
    total_chars: int
    status: int
    risk_count: int
    high_count: int
    medium_count: int
    low_count: int
    created_at: datetime | None = None


class ContractPageOut(BaseModel):
    """合同分页响应。"""

    items: list[ContractOut] = Field(default_factory=list)
    total: int = 0
    page: int = 1
    page_size: int = 20


class ContractDetailOut(BaseModel):
    """合同详情 + 风险列表。"""

    contract: ContractOut
    risks: list[ContractRiskOut] = Field(default_factory=list)