from __future__ import annotations

from typing import Any


def assess_report(report: dict[str, Any]) -> dict[str, Any]:
    findings = report.get("findings")
    if not isinstance(findings, list):
        return {"risk": "Unknown", "reason": "malformed_report", "confidence_flags": []}

    severities = {str(item.get("severity", "")).lower() for item in findings if isinstance(item, dict)}
    mode = str(report.get("mode") or report.get("scan_mode") or "").lower()
    confidence_flags = ["Low confidence"] if mode in {"static-only", "static_only", "no-llm"} else []

    if severities & {"critical", "high"}:
        return {"risk": "High", "reason": "critical_or_high_finding", "confidence_flags": confidence_flags}
    if "medium" in severities:
        return {"risk": "Medium", "reason": "medium_finding", "confidence_flags": confidence_flags}
    return {
        "risk": "Low",
        "reason": "no_medium_high_or_critical_findings",
        "confidence_flags": confidence_flags,
    }
