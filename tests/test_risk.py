import json
from pathlib import Path

from skill_exchange.risk import assess_report


def _load(name: str) -> dict:
    return json.loads((Path("tests/fixtures/reports") / name).read_text())


def test_clean_static_report_is_low_with_low_confidence():
    assessment = assess_report(_load("skillspector-clean.json"))

    assert assessment["risk"] == "Low"
    assert assessment["confidence_flags"] == ["Low confidence"]
    assert assessment["reason"] == "no_medium_high_or_critical_findings"


def test_medium_report_is_medium():
    assessment = assess_report(_load("skillspector-medium.json"))

    assert assessment["risk"] == "Medium"
    assert assessment["confidence_flags"] == []


def test_high_report_is_high():
    assessment = assess_report(_load("skillspector-high.json"))

    assert assessment["risk"] == "High"
    assert assessment["confidence_flags"] == []


def test_malformed_report_is_unknown():
    assessment = assess_report({"unexpected": "shape"})

    assert assessment["risk"] == "Unknown"
    assert assessment["reason"] == "malformed_report"
