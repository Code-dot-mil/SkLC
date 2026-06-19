from __future__ import annotations

from typing import Any


def assess_report(report: dict[str, Any]) -> dict[str, Any]:
    issues = report.get("issues")
    risk_assessment = report.get("risk_assessment")
    metadata = report.get("metadata") or {}
    if not isinstance(issues, list) or not isinstance(risk_assessment, dict):
        return {"risk": "Unknown", "reason": "malformed_report", "confidence_flags": []}

    severities = {str(item.get("severity", "")).lower() for item in issues if isinstance(item, dict)}
    report_severity = str(risk_assessment.get("severity", "")).lower()
    llm_requested = bool(metadata.get("llm_requested", True))
    confidence_flags = ["Low confidence"] if not llm_requested else []

    if severities & {"critical", "high"} or report_severity in {"critical", "high"}:
        return {"risk": "High", "reason": "critical_or_high_finding", "confidence_flags": confidence_flags}
    if "medium" in severities or report_severity == "medium":
        return {"risk": "Medium", "reason": "medium_finding", "confidence_flags": confidence_flags}
    return {
        "risk": "Low",
        "reason": "no_medium_high_or_critical_findings",
        "confidence_flags": confidence_flags,
    }
