"""风险规则业务用例（《10-合同风险规则配置设计》，极简模型）。

- 一条规则 = 一句话 rule_text + 可选开放维度 category；
- 全局规则维护 + 个人副本（rule_id 关联）覆盖；
- Markdown 导入导出：一句话格式，按 rule_text 幂等。
"""
import logging
from datetime import datetime, timezone
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import BizException
from app.models.risk_rule import RiskRule, RiskRuleCustom
from app.repositories.logs import OperationLogRepository
from app.repositories.risk_rule import RiskRuleCustomRepository, RiskRuleRepository
from app.schemas.risk_rule import (
    RiskRuleCreate,
    RiskRuleImportResult,
    RiskRuleOut,
    RiskRulePageOut,
    RiskRuleUpdate,
)

logger = logging.getLogger(__name__)

CATEGORY_MAX_LENGTH = 32
DOC_TITLES = {"合同风险扫描规则", "Contract Risk Rules", "Rules"}


def _out(rule: RiskRule | RiskRuleCustom, *, source: str = "global") -> RiskRuleOut:
    """ORM -> DTO（source=global/custom）。"""
    return RiskRuleOut(
        id=getattr(rule, "id"),
        rule_text=rule.rule_text.strip(),
        category=rule.category,
        enabled=rule.enabled,
        sort_order=rule.sort_order,
        source=source,
        is_custom=source == "custom",
        created_at=rule.created_at,
        updated_at=rule.updated_at,
    )


def _extract_one_line_rules(content: str) -> list[dict[str, Any]]:
    """解析一句话 Markdown：`# 维度` 下每行 `- 一句话规则` 即一条规则。"""
    rules: list[dict[str, Any]] = []
    category: str | None = None
    for raw in content.splitlines():
        line = raw.strip()
        if line.startswith("# ") and not line.startswith("## "):
            heading = line[2:].strip()
            category = None if heading in DOC_TITLES else heading
        elif line.startswith("- ") and not line.startswith("## "):
            text = line[2:].strip()
            if text and ":" not in text.split(" ", 1)[0]:
                rules.append({"rule_text": text, "category": category})
    return rules


def parse_rule_markdown_detailed(content: str) -> tuple[list[dict[str, Any]], list[str]]:
    """解析 Markdown 返回 (valid_rules, errors)（一句话格式，严格校验）。"""
    rules = _extract_one_line_rules(content)
    valid: list[dict[str, Any]] = []
    errors: list[str] = []
    seen: set[str] = set()
    for idx, item in enumerate(rules, start=1):
        text = item["rule_text"].strip()
        label = f"第{idx}条「{text[:20]}」"
        problems: list[str] = []
        if not text:
            problems.append("规则内容为空")
        if len(text) > 2000:
            problems.append("规则内容过长（最多 2000 字符）")
        cat = item.get("category")
        if cat is not None and (not cat.strip() or len(cat) > CATEGORY_MAX_LENGTH):
            problems.append("维度名称非法（1~32 字符）")
        if text in seen:
            problems.append("规则内容重复")
        if problems:
            errors.append(f"{label}：{'；'.join(problems)}")
            continue
        seen.add(text)
        valid.append({
            "rule_text": text,
            "category": (cat or None),
            "enabled": True,
            "sort_order": idx * 10,
        })
    return valid, errors


def parse_rule_markdown(content: str) -> list[dict[str, Any]]:
    """解析 Markdown 返回有效规则（便捷函数）。"""
    return parse_rule_markdown_detailed(content)[0]


def build_rule_markdown(rules: list[RiskRule]) -> str:
    """导出结构化 Markdown：按维度分组，每行一句话规则。"""
    lines = [
        "# 合同风险扫描规则",
        "",
        f"> 导出时间：{datetime.now(timezone.utc).astimezone().strftime('%Y-%m-%d %H:%M:%S')}",
        f"> 规则数量：{len(rules)}",
        "",
    ]
    grouped: dict[str | None, list[RiskRule]] = {}
    for rule in rules:
        grouped.setdefault(rule.category, []).append(rule)
    for category in grouped:
        lines.append(f"# {category or '未分类'}")
        lines.append("")
        for rule in grouped[category]:
            suffix = "  [停用]" if not rule.enabled else ""
            lines.append(f"- {rule.rule_text.strip()}{suffix}")
        lines.append("")
    return "\n".join(lines)


class RiskRuleService:
    """风险规则业务用例。"""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._repo = RiskRuleRepository(session)
        self._custom_repo = RiskRuleCustomRepository(session)
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
        """分页列表（severity 参数已废弃，保留接口兼容）。"""
        items, total = await self._repo.list_rules(
            page=page,
            page_size=page_size,
            keyword=keyword,
            category=category,
            enabled=enabled,
        )
        return RiskRulePageOut(
            items=[_out(r) for r in items], total=total, page=page, page_size=page_size
        )

    async def list_effective(self, user_id: int) -> list[RiskRuleOut]:
        """当前用户生效规则：全局 + 个人副本（同 rule_id 个人优先）。"""
        globals_map = {r.id: _out(r, source="global") for r in await self._repo.list_export()}
        customs = {c.rule_id: _out(c, source="custom") for c in await self._custom_repo.list_by_user(user_id)}
        merged = {**globals_map, **customs}
        return sorted(merged.values(), key=lambda r: (r.sort_order, r.id))

    # ==================== 写操作 ====================

    async def create(
        self, data: RiskRuleCreate, *, operator_id: int, request_meta: dict[str, Any]
    ) -> RiskRuleOut:
        """新建规则：一句话 + 可选维度。"""
        text = data.rule_text.strip()
        if await self._repo.get_by_rule_text(text) is not None:
            raise BizException(20001, "规则已存在")
        rule = RiskRule(
            rule_text=text,
            category=data.category or None,
            enabled=data.enabled,
            sort_order=data.sort_order,
            created_by=operator_id,
            updated_by=operator_id,
        )
        await self._repo.add(rule)
        await self._session.refresh(rule)
        out = _out(rule)
        await self._audit("risk_rule.create", "POST", "/api/v1/admin/risk-rules",
                          {"rule_text": text[:120]}, operator_id, request_meta)
        await self._session.commit()
        logger.info("risk rule created", extra={"operator_id": operator_id, "rule_id": rule.id})
        return out

    async def update(
        self, rule_id: int, data: RiskRuleUpdate, *, operator_id: int, request_meta: dict[str, Any]
    ) -> RiskRuleOut:
        """更新规则（未传字段沿用旧值）。"""
        rule = await self._get_or_404(rule_id)
        if data.rule_text is not None:
            rule.rule_text = data.rule_text.strip()
        if data.category is not None:
            rule.category = data.category
        if data.enabled is not None:
            rule.enabled = data.enabled
        if data.sort_order is not None:
            rule.sort_order = data.sort_order
        rule.updated_by = operator_id
        await self._session.flush()
        await self._session.refresh(rule)
        out = _out(rule)
        await self._audit("risk_rule.update", "PUT", f"/api/v1/admin/risk-rules/{rule_id}",
                          {"rule_text": rule.rule_text[:120]}, operator_id, request_meta)
        await self._session.commit()
        return out

    async def delete(self, rule_id: int, *, operator_id: int, request_meta: dict[str, Any]) -> None:
        """软删除全局规则（个人副本随外键级联删除）。"""
        rule = await self._get_or_404(rule_id)
        await self._repo.soft_delete(rule)
        await self._audit("risk_rule.delete", "DELETE", f"/api/v1/admin/risk-rules/{rule_id}",
                          {"rule_text": rule.rule_text[:120]}, operator_id, request_meta)
        await self._session.commit()

    # ==================== 个人副本 ====================

    async def upsert_custom(self, user_id: int, rule_id: int, data: RiskRuleUpdate) -> RiskRuleOut:
        """保存个人副本（首次从全局快照，之后仅改本人）。"""
        glob = await self._repo.get_by_id(rule_id)
        if glob is None:
            raise BizException(10001, "Not Found", http_status=404)
        custom = await self._custom_repo.get_by_user_rule(user_id, rule_id)
        if custom is None:
            custom = RiskRuleCustom(
                user_id=user_id,
                rule_id=rule_id,
                rule_text=glob.rule_text,
                category=glob.category,
                enabled=glob.enabled,
                sort_order=glob.sort_order,
            )
            self._session.add(custom)
        if data.rule_text is not None:
            custom.rule_text = data.rule_text.strip()
        if data.category is not None:
            custom.category = data.category
        if data.enabled is not None:
            custom.enabled = data.enabled
        if data.sort_order is not None:
            custom.sort_order = data.sort_order
        await self._session.flush()
        await self._session.refresh(custom)
        out = _out(custom, source="custom")
        await self._session.commit()
        return out

    async def delete_custom(self, user_id: int, rule_id: int) -> None:
        """恢复单条默认：删除该用户对应个人副本。"""
        await self._custom_repo.delete_by_user_rule(user_id, rule_id)
        await self._session.commit()

    async def restore_default(self, user_id: int) -> None:
        """一键恢复默认：删除当前用户全部个人副本。"""
        await self._custom_repo.delete_all_by_user(user_id)
        await self._session.commit()

    # ==================== Markdown 导入导出 ====================

    async def import_markdown(
        self, content: str, *, operator_id: int, request_meta: dict[str, Any]
    ) -> RiskRuleImportResult:
        """导入 Markdown：严格校验，按 rule_text 幂等 upsert；错误时不写入。"""
        valid, errors = parse_rule_markdown_detailed(content)
        if errors:
            detail = "；".join(errors[:10])
            if len(errors) > 10:
                detail += f"；……共 {len(errors)} 条错误"
            raise BizException(20002, f"Markdown 校验失败：{detail}")

        created = 0
        updated = 0
        for item in valid:
            existing = await self._repo.get_by_rule_text(item["rule_text"])
            if existing is None:
                rule = RiskRule(
                    rule_text=item["rule_text"],
                    category=item["category"],
                    enabled=True,
                    sort_order=item["sort_order"],
                    created_by=operator_id,
                    updated_by=operator_id,
                )
                await self._repo.add(rule)
                created += 1
            else:
                if item["category"] is not None and existing.category != item["category"]:
                    existing.category = item["category"]
                existing.enabled = True
                existing.updated_by = operator_id
                updated += 1
        await self._audit(
            "risk_rule.import", "POST", "/api/v1/admin/risk-rules/import",
            {"created": created, "updated": updated}, operator_id, request_meta,
        )
        await self._session.commit()
        logger.info(
            "risk rule imported",
            extra={"operator_id": operator_id, "created_count": created, "updated_count": updated},
        )
        return RiskRuleImportResult(created=created, updated=updated, skipped=0)

    async def export_markdown(self) -> str:
        """导出全部规则 Markdown。"""
        rules = await self._repo.list_export()
        return build_rule_markdown(rules)

    # ==================== 私有 ====================

    async def _get_or_404(self, rule_id: int) -> RiskRule:
        rule = await self._repo.get_by_id(rule_id)
        if rule is None:
            raise BizException(10001, "Not Found", http_status=404)
        return rule

    async def _audit(
        self, action: str, method: str, path: str, body: dict[str, Any],
        operator_id: int, request_meta: dict[str, Any],
    ) -> None:
        await self._audit_repo.add_log(
            user_id=operator_id, module="risk", action=action, method=method, path=path,
            request_body=body, response_code=0, ip=request_meta.get("ip"),
            user_agent=request_meta.get("user_agent"), duration_ms=request_meta.get("duration_ms"),
            trace_id=request_meta.get("trace_id"),
        )
