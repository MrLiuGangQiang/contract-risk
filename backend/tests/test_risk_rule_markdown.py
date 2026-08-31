"""Unit tests for risk rule Markdown parsing/export (design 10 section 4).

Pure function tests only; no shared database access.
"""
from app.models.risk_rule import RiskRule
from app.services.risk_rule_service import (
    build_rule_markdown,
    parse_rule_markdown,
    parse_rule_markdown_detailed,
)


def test_parse_one_line_rules_from_h1_heading() -> None:
    """一句话格式：# 一级标题 = 维度，其下 - 一句话 = 一条规则。"""
    md = """# 合同风险扫描规则

# 财务风险
- 付款不得一次性全额付款且无质保金
- 必须明确逾期付款的违约责任

# 知识产权
- 必须明确知识产权归属
"""
    rules = parse_rule_markdown(md)
    assert len(rules) == 3
    assert rules[0]["rule_text"] == "付款不得一次性全额付款且无质保金"
    assert rules[0]["category"] == "财务风险"
    assert rules[0]["enabled"] is True
    assert rules[1]["category"] == "财务风险"
    assert rules[2]["rule_text"] == "必须明确知识产权归属"
    assert rules[2]["category"] == "知识产权"


def test_document_titles_are_not_dimensions() -> None:
    """文档标题（合同风险扫描规则 / Rules）不作为维度，其下规则维度为空。"""
    md = """# 合同风险扫描规则

# Rules
- payment must be clear
"""
    rules = parse_rule_markdown(md)
    assert len(rules) == 1
    assert rules[0]["category"] is None


def test_parse_skips_key_value_lines() -> None:
    """key: value 行（旧完整字段格式）不当作一句话规则。"""
    md = """# 财务风险
- code: FIN_PAY
- 付款不得一次性全额付款且无质保金
"""
    rules = parse_rule_markdown(md)
    assert len(rules) == 1
    assert rules[0]["rule_text"] == "付款不得一次性全额付款且无质保金"


def test_parse_detailed_reports_duplicate() -> None:
    """重复规则报错，不进入 valid。"""
    md = """# 财务风险
- 付款不得一次性全额付款且无质保金
- 付款不得一次性全额付款且无质保金
"""
    valid, errors = parse_rule_markdown_detailed(md)
    assert len(valid) == 1
    assert len(errors) == 1
    assert "重复" in errors[0]


def test_parse_detailed_reports_too_long() -> None:
    """超长规则（>2000 字符）报错。"""
    md = "# 财务风险\n- " + "长" * 2001 + "\n"
    valid, errors = parse_rule_markdown_detailed(md)
    assert valid == []
    assert len(errors) == 1
    assert "过长" in errors[0]


def test_build_and_parse_roundtrip() -> None:
    """导出格式 A 再解析，rule_text/category 保持。"""
    rules = [
        RiskRule(id=1, rule_text="付款不得一次性全额付款且无质保金", category="财务风险", enabled=True, sort_order=10),
        RiskRule(id=2, rule_text="必须明确知识产权归属", category="知识产权", enabled=True, sort_order=20),
    ]
    md = build_rule_markdown(rules)
    assert "# 财务风险" in md
    assert "# 知识产权" in md
    parsed, errors = parse_rule_markdown_detailed(md)
    assert errors == []
    assert {r["rule_text"]: r["category"] for r in parsed} == {
        "付款不得一次性全额付款且无质保金": "财务风险",
        "必须明确知识产权归属": "知识产权",
    }


def test_parse_empty_content_returns_empty() -> None:
    """空内容返回空规则与空错误。"""
    valid, errors = parse_rule_markdown_detailed("")
    assert valid == []
    assert errors == []
