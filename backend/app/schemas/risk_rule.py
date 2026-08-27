"""风险规则 DTO（《10-合同风险规则配置设计》第 4 节）。"""
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

RiskRuleCategory = Literal["payment", "breach", "subject", "ip", "dispute", "other"]
RiskRuleSeverity = Literal["high", "medium", "low"]


class RiskRuleCreate(BaseModel):
    """新建规则请求（code 创建后不可修改）。"""

    code: str = Field(min_length=1, max_length=64, pattern=r"^[A-Z0-9_]+$")
    name: str = Field(min_length=1, max_length=128)
    category: RiskRuleCategory
    severity: RiskRuleSeverity
    keywords: list[str] = Field(default_factory=list, max_length=50)
    description: str = Field(min_length=1, max_length=2000)
    suggestion: str = Field(min_length=1, max_length=2000)
    enabled: bool = True
    sort_order: int = Field(default=0, ge=0, le=9999)


class RiskRuleUpdate(BaseModel):
    """更新规则请求（code 不可修改）。"""

    name: str = Field(min_length=1, max_length=128)
    category: RiskRuleCategory
    severity: RiskRuleSeverity
    keywords: list[str] = Field(default_factory=list, max_length=50)
    description: str = Field(min_length=1, max_length=2000)
    suggestion: str = Field(min_length=1, max_length=2000)
    enabled: bool = True
    sort_order: int = Field(default=0, ge=0, le=9999)


class RiskRuleOut(BaseModel):
    """规则响应。"""

    id: int
    code: str
    name: str
    category: str
    severity: str
    keywords: list[str] = Field(default_factory=list)
    description: str
    suggestion: str
    enabled: bool
    sort_order: int
    created_at: datetime | None = None
    updated_at: datetime | None = None


class RiskRulePageOut(BaseModel):
    """规则分页响应。"""

    items: list[RiskRuleOut] = Field(default_factory=list)
    total: int = 0
    page: int = 1
    page_size: int = 20


class RiskRuleImportIn(BaseModel):
    """导入 Markdown 请求（前端读取文件后提交文本内容）。"""

    content: str = Field(min_length=1, max_length=2_000_000)


class RiskRuleImportResult(BaseModel):
    """导入结果。"""

    created: int = 0
    updated: int = 0
    skipped: int = 0
