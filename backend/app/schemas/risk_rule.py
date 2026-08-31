"""风险规则 DTO（《10-合同风险规则配置设计》第 4 节）。"""
from datetime import datetime

from pydantic import BaseModel, Field

# 维度为开放格式（《10》第 4 节）：Markdown 一级标题即维度名，可自定义任意维度
CATEGORY_MAX_LENGTH = 32


class RiskRuleCreate(BaseModel):
    """新建规则请求：只需一句话 rule_text，category 可选。"""

    rule_text: str = Field(min_length=1, max_length=2000)
    category: str | None = Field(default=None, max_length=CATEGORY_MAX_LENGTH)
    enabled: bool = True
    sort_order: int = Field(default=0, ge=0, le=9999)


class RiskRuleUpdate(BaseModel):
    """更新规则请求：未传字段沿用旧值。"""

    rule_text: str | None = Field(default=None, max_length=2000)
    category: str | None = Field(default=None, max_length=CATEGORY_MAX_LENGTH)
    enabled: bool | None = None
    sort_order: int | None = Field(default=None, ge=0, le=9999)


class RiskRuleOut(BaseModel):
    """规则响应（source=global/custom，标识来源）。"""

    id: int
    rule_text: str
    category: str | None = None
    enabled: bool
    sort_order: int
    source: str = "global"
    is_custom: bool = False
    created_at: datetime | None = None
    updated_at: datetime | None = None


class RiskRulePageOut(BaseModel):
    """规则分页响应。"""

    items: list[RiskRuleOut] = Field(default_factory=list)
    total: int = 0
    page: int = 1
    page_size: int = 20


class RiskRuleCustomIn(RiskRuleUpdate):
    """个人副本保存请求（code 在路径中，不随 body 修改）。"""


class RiskRuleImportIn(BaseModel):
    """导入 Markdown 请求（前端读取文件后提交文本内容）。"""

    content: str = Field(min_length=1, max_length=2_000_000)


class RiskRuleImportResult(BaseModel):
    """导入结果。"""

    created: int = 0
    updated: int = 0
    skipped: int = 0
