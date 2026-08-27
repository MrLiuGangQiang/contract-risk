"""合同风险识别业务用例（《11-合同风险识别核心功能设计》）。

上传合同 → 文本解析 → 当前用户生效规则关键词匹配 → 风险结果落库。
同步执行；文件大小/类型校验在 API 与 Service 双层实施。
"""
import asyncio
import io
import logging
import re
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from pypdf import PdfReader
from docx import Document
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.exceptions import BizException
from app.domain.constants import (
    CONTRACT_ALLOWED_EXTENSIONS,
    CONTRACT_MAX_SIZE,
    CONTRACT_STATUS_DONE,
    CONTRACT_STATUS_FAILED,
)
from app.models.contract import Contract, ContractRisk
from app.repositories.contract import ContractRepository
from app.repositories.logs import OperationLogRepository
from app.schemas.contract import ContractDetailOut, ContractOut, ContractPageOut, ContractRiskOut
from app.services.risk_rule_service import RiskRuleService

logger = logging.getLogger(__name__)

_SEVERITY_ORDER = {"high": 0, "medium": 1, "low": 2}
_SNIPPET_RADIUS = 60


def _decode_text(data: bytes) -> str:
    """Decode txt with UTF-8 then GB18030 fallback."""
    for encoding in ("utf-8", "gb18030"):
        try:
            return data.decode(encoding)
        except UnicodeDecodeError:
            continue
    return data.decode("utf-8", errors="ignore")


def _parse_document(ext: str, data: bytes) -> str:
    """Extract plain text from txt/pdf/docx."""
    if ext == "txt":
        return _decode_text(data)
    if ext == "pdf":
        reader = PdfReader(io.BytesIO(data))
        return "\n".join((page.extract_text() or "") for page in reader.pages)
    if ext == "docx":
        doc = Document(io.BytesIO(data))
        parts = [p.text for p in doc.paragraphs if p.text.strip()]
        for table in doc.tables:
            for row in table.rows:
                parts.append(" | ".join(cell.text for cell in row.cells))
        return "\n".join(parts)
    raise BizException(20002, "不支持的文件格式，仅支持 txt/pdf/docx")


def _extract_snippet(text: str, keyword: str) -> str:
    """Return context around first keyword occurrence."""
    match = re.search(re.escape(keyword), text, flags=re.IGNORECASE)
    if not match:
        return ""
    start = max(0, match.start() - _SNIPPET_RADIUS)
    end = min(len(text), match.end() + _SNIPPET_RADIUS)
    prefix = "..." if start > 0 else ""
    suffix = "..." if end < len(text) else ""
    return f"{prefix}{text[start:end]}{suffix}"


def _scan_text(text: str, rules: list[Any]) -> list[dict[str, Any]]:
    """Keyword matching against effective rules; returns sorted hits."""
    hits: list[dict[str, Any]] = []
    for rule in rules:
        if not rule.enabled:
            continue
        matched: list[str] = []
        snippet = ""
        for keyword in rule.keywords:
            if not keyword:
                continue
            if re.search(re.escape(keyword), text, flags=re.IGNORECASE):
                matched.append(keyword)
                if not snippet:
                    snippet = _extract_snippet(text, keyword)
        if matched:
            hits.append(
                {
                    "rule_code": rule.code,
                    "rule_name": rule.name,
                    "category": rule.category,
                    "severity": rule.severity,
                    "matched_keywords": matched,
                    "snippet": snippet,
                    "description": rule.description,
                    "suggestion": rule.suggestion,
                    "sort_order": rule.sort_order,
                }
            )
    hits.sort(key=lambda h: (_SEVERITY_ORDER.get(h["severity"], 9), h["sort_order"], h["rule_code"]))
    return hits


def _risk_out(risk: ContractRisk) -> ContractRiskOut:
    """ORM -> DTO."""
    return ContractRiskOut(
        id=risk.id,
        rule_code=risk.rule_code,
        rule_name=risk.rule_name,
        category=risk.category,
        severity=risk.severity,
        matched_keywords=risk.matched_keywords or [],
        snippet=risk.snippet,
        description=risk.description,
        suggestion=risk.suggestion,
        sort_order=risk.sort_order,
        created_at=risk.created_at,
    )


def _contract_out(contract: Contract) -> ContractOut:
    """ORM -> DTO."""
    return ContractOut(
        id=contract.id,
        user_id=contract.user_id,
        file_name=contract.file_name,
        file_ext=contract.file_ext,
        file_size=contract.file_size,
        total_chars=contract.total_chars,
        status=contract.status,
        risk_count=contract.risk_count,
        high_count=contract.high_count,
        medium_count=contract.medium_count,
        low_count=contract.low_count,
        created_at=contract.created_at,
    )


class ContractRiskService:
    """合同风险识别业务用例。"""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._repo = ContractRepository(session)
        self._risk_rule_service = RiskRuleService(session)
        self._audit_repo = OperationLogRepository(session)

    async def upload(
        self, *, user_id: int, file_name: str, content: bytes, request_meta: dict[str, Any]
    ) -> ContractDetailOut:
        """上传并同步扫描合同。"""
        ext = file_name.rsplit(".", 1)[-1].lower() if "." in file_name else ""
        if ext not in CONTRACT_ALLOWED_EXTENSIONS:
            raise BizException(20002, "仅支持 txt/pdf/docx 文件")
        if not content:
            raise BizException(20002, "文件内容为空")
        if len(content) > CONTRACT_MAX_SIZE:
            raise BizException(20002, "文件不能超过 20MB")

        text = await asyncio.to_thread(_parse_document, ext, content)
        rules = await self._risk_rule_service.list_effective(user_id)
        hits = _scan_text(text, rules)

        settings = get_settings()
        upload_path = Path(settings.upload_dir)
        upload_path.mkdir(parents=True, exist_ok=True)
        stored_name = f"{uuid.uuid4().hex}.{ext}"
        stored_path = upload_path / stored_name
        stored_path.write_bytes(content)

        contract = Contract(
            user_id=user_id,
            file_name=file_name[:255],
            file_path=str(stored_path),
            file_ext=ext,
            file_size=len(content),
            text_content=text,
            total_chars=len(text),
            status=CONTRACT_STATUS_DONE,
            created_by=user_id,
            updated_by=user_id,
        )
        await self._repo.add_contract(contract)
        risks = await self._save_risks(contract, user_id, hits)
        await self._update_contract_counts(contract, hits)

        await self._audit(
            "contract.upload", "POST", "/api/v1/contracts/upload",
            {"file_name": file_name, "risk_count": len(hits)}, user_id, request_meta,
        )
        await self._session.commit()
        logger.info("contract uploaded", extra={"user_id": user_id, "contract_id": contract.id})
        return ContractDetailOut(contract=_contract_out(contract), risks=[_risk_out(r) for r in risks])

    async def list_contracts(
        self,
        *,
        user_id: int,
        page: int,
        page_size: int,
        keyword: str | None,
        severity: str | None,
    ) -> ContractPageOut:
        """合同分页列表。"""
        items, total = await self._repo.list_contracts(
            user_id=user_id, page=page, page_size=page_size, keyword=keyword, severity=severity
        )
        return ContractPageOut(
            items=[_contract_out(c) for c in items], total=total, page=page, page_size=page_size
        )

    async def get_detail(self, *, user_id: int, contract_id: int) -> ContractDetailOut:
        """合同详情 + 风险列表。"""
        contract = await self._get_or_404(user_id, contract_id)
        risks = await self._repo.list_risks(contract.id)
        return ContractDetailOut(contract=_contract_out(contract), risks=[_risk_out(r) for r in risks])

    async def rescan(self, *, user_id: int, contract_id: int, request_meta: dict[str, Any]) -> ContractDetailOut:
        """重新扫描：用当前生效规则替换风险结果。"""
        contract = await self._get_or_404(user_id, contract_id)
        rules = await self._risk_rule_service.list_effective(user_id)
        hits = _scan_text(contract.text_content, rules)
        risks = await self._save_risks(contract, user_id, hits)
        await self._update_contract_counts(contract, hits)
        await self._audit(
            "contract.rescan", "POST", f"/api/v1/contracts/{contract_id}/rescan",
            {"risk_count": len(hits)}, user_id, request_meta,
        )
        await self._session.commit()
        logger.info("contract rescanned", extra={"user_id": user_id, "contract_id": contract_id})
        return ContractDetailOut(contract=_contract_out(contract), risks=[_risk_out(r) for r in risks])

    async def delete(self, *, user_id: int, contract_id: int, request_meta: dict[str, Any]) -> None:
        """软删除合同（并删除风险结果）。"""
        contract = await self._get_or_404(user_id, contract_id)
        await self._repo.soft_delete_contract(contract)
        await self._audit(
            "contract.delete", "DELETE", f"/api/v1/contracts/{contract_id}",
            {"file_name": contract.file_name}, user_id, request_meta,
        )
        await self._session.commit()
        logger.info("contract deleted", extra={"user_id": user_id, "contract_id": contract_id})

    # ==================== 私有 ====================

    async def _save_risks(self, contract: Contract, user_id: int, hits: list[dict[str, Any]]) -> list[ContractRisk]:
        """写入风险结果并返回实体列表（不提交）。"""
        risks = [
            ContractRisk(
                contract_id=contract.id,
                user_id=user_id,
                rule_code=h["rule_code"],
                rule_name=h["rule_name"],
                category=h["category"],
                severity=h["severity"],
                matched_keywords=h["matched_keywords"],
                snippet=h["snippet"],
                description=h["description"],
                suggestion=h["suggestion"],
                sort_order=h["sort_order"],
            )
            for h in hits
        ]
        await self._repo.replace_risks(contract.id, user_id, risks)
        return risks

    async def _update_contract_counts(self, contract: Contract, hits: list[dict[str, Any]]) -> None:
        """更新合同风险统计。"""
        contract.risk_count = len(hits)
        contract.high_count = sum(1 for h in hits if h["severity"] == "high")
        contract.medium_count = sum(1 for h in hits if h["severity"] == "medium")
        contract.low_count = sum(1 for h in hits if h["severity"] == "low")
        contract.updated_by = contract.created_by
        await self._session.flush()

    async def _get_or_404(self, user_id: int, contract_id: int) -> Contract:
        contract = await self._repo.get_contract(user_id, contract_id)
        if contract is None:
            raise BizException(10001, "Not Found", http_status=404)
        return contract

    async def _audit(
        self, action: str, method: str, path: str, body: dict[str, Any], operator_id: int,
        request_meta: dict[str, Any],
    ) -> None:
        await self._audit_repo.add_log(
            user_id=operator_id, module="contract", action=action, method=method, path=path,
            request_body=body, response_code=0, ip=request_meta.get("ip"),
            user_agent=request_meta.get("user_agent"), duration_ms=request_meta.get("duration_ms"),
            trace_id=request_meta.get("trace_id"),
        )