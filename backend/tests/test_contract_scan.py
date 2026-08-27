"""Contract risk scanning pure function tests (design 11 section 2).

No DB/network access; validates text parse and keyword matching ordering.
"""
from app.models.risk_rule import RiskRule
from app.services.contract_risk_service import _scan_text


def test_scan_text_high_severity_first() -> None:
    """Hits should be ordered by severity then sort_order."""
    low = RiskRule(
        id=1, code="GENERAL", name="general", category="general", severity="low",
        keywords=["foo"], description="d", suggestion="s", enabled=True, sort_order=0,
    )
    high = RiskRule(
        id=2, code="TECH", name="tech", category="technology", severity="high",
        keywords=["foo"], description="d", suggestion="s", enabled=True, sort_order=10,
    )
    hits = _scan_text("some foo text", [low, high])
    assert [h["rule_code"] for h in hits] == ["TECH", "GENERAL"]
    assert hits[0]["matched_keywords"] == ["foo"]
    assert "foo" in hits[0]["snippet"]


def test_scan_text_skips_disabled_rule() -> None:
    """Disabled rules must not produce hits."""
    disabled = RiskRule(
        id=1, code="DISABLED", name="disabled", category="general", severity="high",
        keywords=["hidden"], description="d", suggestion="s", enabled=False, sort_order=0,
    )
    assert _scan_text("hidden text", [disabled]) == []
