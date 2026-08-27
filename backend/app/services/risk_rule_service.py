"""风险规则业务用例（《10-合同风险规则配置设计》）。

- 在线编辑：列表/创建/更新/软删除；
- Markdown 导入导出：按 code 幂等 upsert；
- 仅超管（risk:rule:manage）可访问，写操作全部审计。
"""
import logging
from datetime import datetime, timezone
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import BizException
from app.domain.constants import (
    RISK_RULE_CATEGORY_BREACH,
    RISK_RULE_CATEGORY_DISPUTE,
    RISK_RULE_CATEGORY_IP,
    RISK_RULE_CATEGORY_OTHER,
    RISK_RULE_CATEGORY_PAYMENT,
    RISK_RULE_CATEGORY_SUBJECT,
    RISK_RULE_SEVERITY_HIGH,
    RISK_RULE_SEVERITY_LOW,
    RISK_RULE_SEVERITY_MEDIUM,
)
from app.models.risk_rule import RiskRule
from app.repositories.logs import OperationLogRepository
from app.repositories.risk_rule import RiskRuleRepository
from app.schemas.risk_rule import (
    RiskRuleCreate,
    RiskRuleImportResult,
    RiskRuleOut,
    RiskRulePageOut,
    RiskRuleUpdate,
)

logger = logging.getLogger(__name__)

RISK_RULE_CATEGORIES = {
    RISK_RULE_CATEGORY_PAYMENT,
    RISK_RULE_CATEGORY_BREACH,
    RISK_RULE_CATEGORY_SUBJECT,
    RISK_RULE_CATEGORY_IP,
    RISK_RULE_CATEGORY_DISPUTE,
    RISK_RULE_CATEGORY_OTHER,
}
RISK_RULE_SEVERITIES = {
    RISK_RULE_SEVERITY_HIGH,
    RISK_RULE_SEVERITY_MEDIUM,
    RISK_RULE_SEVERITY_LOW,
}


def _out(rule: RiskRule) -> RiskRuleOut:
    """ORM -> DTO。"""
    return RiskRuleOut(
        id=rule.id,
        code=rule.code,
        name=rule.name,
        category=rule.category,
        severity=rule.severity,
        keywords=rule.keywords or [],
        description=rule.description,
        suggestion=rule.suggestion,
        enabled=rule.enabled,
        sort_order=rule.sort_order,
        created_at=rule.created_at,
        updated_at=rule.updated_at,
    )


def _parse_bool(value: str, default: bool = True) -> bool:
    """Markdown 布尔值解析。"""
    return value.strip().lower() not in {"false", "0", "no", "否", "off"}


def _parse_keywords(value: str) -> list[str]:
    """Markdown 关键词解析：逗号分隔。"""
    return [item.strip() for item in value.split(",") if item.strip()]


def parse_rule_markdown(content: str) -> list[dict[str, Any]]:
    """解析结构化 Markdown 规则（《10》第 3 节）。

    每个 `## 名称` 开始一条规则，后续 `- key: value` 为字段。
    返回经校验的字段字典列表；非法条目由调用方跳过。
    """
    rules: list[dict[str, Any]] = []
    current: dict[str, Any] | None = None

    for raw in content.splitlines():
        line = raw.strip()
        if line.startswith("## "):
            if current is not None:
                rules.append(current)
            current = {"name": line[3:].strip(), "_fields": {}}
        elif current is not None and line.startswith("- "):
            pair = line[2:]
            if ":" not in pair:
                continue
            key, _, value = pair.partition(":")
            current["_fields"][key.strip()] = value.strip()
    if current is not None:
        rules.append(current)

    valid: list[dict[str, Any]] = []
    for raw_rule in rules:
        fields = raw_rule["_fields"]
        code = fields.get("code", "")
        name = raw_rule.get("name", "")
        category = fields.get("category", "")
        severity = fields.get("severity", "")
        description = fields.get("description", "")
        suggestion = fields.get("suggestion", "")
        if not code or not name or category not in RISK_RULE_CATEGORIES:
            continue
        if severity not in RISK_RULE_SEVERITIES:
            continue
        if not description or not suggestion:
            continue
        try:
            sort_order = int(fields.get("sort_order", "0") or "0")
        except ValueError:
            sort_order = 0
        valid.append(
            {
                "code": code[:64],
                "name": name[:128],
                "category": category,
                "severity": severity,
                "keywords": _parse_keywords(fields.get("keywords", ""))[:50],
                "description": description[:2000],
                "suggestion": suggestion[:2000],
                "enabled": _parse_bool(fields.get("enabled", "true")),
                "sort_order": max(0, min(9999, sort_order)),
            }
        )
    return valid


def build_rule_markdown(rules: list[RiskRule]) -> str:
    """导出结构化 Markdown（《10》第 3 节）。"""
    lines = [
        "# 合同风险扫描规则",
        "",
        f"> 导出时间：{datetime.now(timezone.utc).astimezone().strftime('%Y-%m-%d %H:%M:%S')}",
        f"> 规则数量：{len(rules)}",
        "",
    ]
    for rule in rules:
        lines.extend(
            [
                f"## {rule.name}",
                f"- code: {rule.code}",
                f"- category: {rule.category}",
                f"- severity: {rule.severity}",
                f"- enabled: {str(rule.enabled).lower()}",
                f"- sort_order: {rule.sort_order}",
                f"- keywords: {', '.join(rule.keywords or [])}",
                f"- description: {rule.description}",
                f"- suggestion: {rule.suggestion}",
                "",
            ]
        )
    return "\n".join(lines)


class RiskRuleService:
    """风险规则业务用例。"""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._repo = RiskRuleRepository(session)
        self._audit_repo = OperationLogRepository(session)

    # ==================== 查询 ====================

    async def list_rules(
        self,
        *,
        page: int,
        page_size: int,
        keyword: str | None,
        category: str | None,
        severity: str | None,
        enabled: bool | None,
    ) -> RiskRulePageOut:
        """分页列表。"""
        items, total = await self._repo.list_rules(
            page=page,
            page_size=page_size,
            keyword=keyword,
            category=category,
            severity=severity,
            enabled=enabled,
        )
        return RiskRulePageOut(
            items=[_out(r) for r in items], total=total, page=page, page_size=page_size
        )

    # ==================== 写操作 ====================

    async def create(
        self, data: RiskRuleCreate, *, operator_id: int, request_meta: dict[str, Any]
    ) -> RiskRuleOut:
        """新建规则（code 唯一）。"""
        if await self._repo.get_by_code(data.code) is not None:
            raise BizException(20001, "规则编码已存在")
        rule = RiskRule(code=data.code, name=data.name, category=data.category,
                        severity=data.severity, keywords=data.keywords,
                        description=data.description, suggestion=data.suggestion,
                        enabled=data.enabled, sort_order=data.sort_order,
                        created_by=operator_id, updated_by=operator_id)
        await self._repo.add(rule)
        await self._session.refresh(rule)
        out = _out(rule)
        await self._audit("risk_rule.create", "POST", "/api/v1/admin/risk-rules",
                          {"code": data.code, "name": data.name}, operator_id, request_meta)
        await self._session.commit()
        logger.info("risk rule created", extra={"operator_id": operator_id, "rule_id": rule.id})
        return out

    async def update(
        self, rule_id: int, data: RiskRuleUpdate, *, operator_id: int, request_meta: dict[str, Any]
    ) -> RiskRuleOut:
        """更新规则（code 不可修改）。"""
        rule = await self._get_or_404(rule_id)
        rule.name = data.name
        rule.category = data.category
        rule.severity = data.severity
        rule.keywords = data.keywords
        rule.description = data.description
        rule.suggestion = data.suggestion
        rule.enabled = data.enabled
        rule.sort_order = data.sort_order
        rule.updated_by = operator_id
        await self._session.flush()
        await self._session.refresh(rule)
        out = _out(rule)
        await self._audit("risk_rule.update", "PUT", f"/api/v1/admin/risk-rules/{rule_id}",
                          {"code": rule.code}, operator_id, request_meta)
        await self._session.commit()
        logger.info("risk rule updated", extra={"operator_id": operator_id, "rule_id": rule_id})
        return out

    async def delete(self, rule_id: int, *, operator_id: int, request_meta: dict[str, Any]) -> None:
        """软删除规则。"""
        rule = await self._get_or_404(rule_id)
        rule.deleted_at = datetime.now(timezone.utc)
        rule.updated_by = operator_id
        await self._session.flush()
        await self._audit("risk_rule.delete", "DELETE", f"/api/v1/admin/risk-rules/{rule_id}",
                          {"code": rule.code}, operator_id, request_meta)
        await self._session.commit()
        logger.info("risk rule deleted", extra={"operator_id": operator_id, "rule_id": rule_id})

    # ==================== 导入导出 ====================

    async def export_markdown(self) -> str:
        """导出全部规则为 Markdown。"""
        rules = await self._repo.list_export()
        return build_rule_markdown(rules)

    async def import_markdown(
        self, content: str, *, operator_id: int, request_meta: dict[str, Any]
    ) -> RiskRuleImportResult:
        """导入 Markdown：按 code 幂等 upsert，非法条目跳过。"""
        parsed = parse_rule_markdown(content)
        created = 0
        updated = 0
        skipped = len(parsed)
        for item in parsed:
            skipped -= 1
            existing = await self._repo.get_by_code(item["code"])
            if existing is None:
                rule = RiskRule(
                    code=item["code"], name=item["name"], category=item["category"],
                    severity=item["severity"], keywords=item["keywords"],
                    description=item["description"], suggestion=item["suggestion"],
                    enabled=item["enabled"], sort_order=item["sort_order"],
                    created_by=operator_id, updated_by=operator_id,
                )
                await self._repo.add(rule)
                created += 1
            else:
                existing.name = item["name"]
                existing.category = item["category"]
                existing.severity = item["severity"]
                existing.keywords = item["keywords"]
                existing.description = item["description"]
                existing.suggestion = item["suggestion"]
                existing.enabled = item["enabled"]
                existing.sort_order = item["sort_order"]
                existing.updated_by = operator_id
                updated += 1
        await self._audit(
            "risk_rule.import", "POST", "/api/v1/admin/risk-rules/import",
            {"created": created, "updated": updated, "skipped": skipped},
            operator_id, request_meta,
        )
        await self._session.commit()
        logger.info(
            "risk rule imported",
            extra={"operator_id": operator_id, "created": created, "updated": updated, "skipped": skipped},
        )
        return RiskRuleImportResult(created=created, updated=updated, skipped=skipped)

    # ==================== 私有 ====================

    async def _get_or_404(self, rule_id: int) -> RiskRule:
        """按主键查询；不存在时 404。"""
        rule = await self._repo.get_by_id(rule_id)
        if rule is None:
            raise BizException(10001, "Not Found", http_status=404)
        return rule

    async def _audit(
        self,
        action: str,
        method: str,
        path: str,
        body: dict[str, Any],
        operator_id: int,
        request_meta: dict[str, Any],
    ) -> None:
        """写入操作审计。"""
        await self._audit_repo.add_log(
            user_id=operator_id,
            module="risk",
            action=action,
            method=method,
            path=path,
            request_body=body,
            response_code=0,
            ip=request_meta.get("ip"),
            user_agent=request_meta.get("user_agent"),
            duration_ms=request_meta.get("duration_ms"),
            trace_id=request_meta.get("trace_id"),
        )
