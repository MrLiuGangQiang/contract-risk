"""Unit tests for risk rule Markdown parsing/export (design 10 section 3).

Pure function tests only; no shared database access.
"""
from app.models.risk_rule import RiskRule
from app.services.risk_rule_service import build_rule_markdown, parse_rule_markdown, parse_rule_markdown_detailed


def test_parse_valid_markdown() -> None:
    """Valid markdown should be parsed into complete rule fields."""
    md = """# Contract Risk Rules

> exported at 2026-08-27 12:00:00

## Payment Term Abnormal
- code: PAYMENT_ABNORMAL
- category: payment
- severity: high
- enabled: false
- sort_order: 3
- keywords: payment, prepay, deposit
- description: risk description
- suggestion: risk suggestion
"""
    rules = parse_rule_markdown(md)
    assert len(rules) == 1
    rule = rules[0]
    assert rule["code"] == "PAYMENT_ABNORMAL"
    assert rule["name"] == "Payment Term Abnormal"
    assert rule["category"] == "payment"
    assert rule["severity"] == "high"
    assert rule["enabled"] is False
    assert rule["sort_order"] == 3
    assert rule["keywords"] == ["payment", "prepay", "deposit"]


def test_parse_skips_invalid_rules() -> None:
    """Rules missing required fields or invalid category should be skipped."""
    md = """# Rules

## Invalid Rule
- code: X
- category: unknown
- severity: high
- description: risk
- suggestion: advice

## Valid Rule
- code: OK_RULE
- category: other
- severity: low
- description: risk
- suggestion: advice
"""
    rules = parse_rule_markdown(md)
    assert len(rules) == 1
    assert rules[0]["code"] == "OK_RULE"


def test_build_and_parse_roundtrip() -> None:
    """Exported markdown parsed back should keep rule fields."""
    rule = RiskRule(
        id=1,
        code="ROUND_TRIP",
        name="Round Trip",
        category="breach",
        severity="medium",
        keywords=["breach", "compensation"],
        description="risk desc",
        suggestion="advice",
        enabled=True,
        sort_order=2,
    )
    md = build_rule_markdown([rule])
    parsed = parse_rule_markdown(md)
    assert len(parsed) == 1
    item = parsed[0]
    assert item["code"] == "ROUND_TRIP"
    assert item["name"] == "Round Trip"
    assert item["category"] == "breach"
    assert item["severity"] == "medium"
    assert item["enabled"] is True
    assert item["sort_order"] == 2
    assert item["keywords"] == ["breach", "compensation"]



def test_parse_detailed_reports_errors() -> None:
    """Strict parser should return human-readable errors for invalid rules."""
    md = """## Bad Rule
- category: unknown
- severity: high
- description: risk
- suggestion: advice
"""
    valid, errors = parse_rule_markdown_detailed(md)
    assert valid == []
    assert len(errors) == 1
    assert "code" in errors[0]
