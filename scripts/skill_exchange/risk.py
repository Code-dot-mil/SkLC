from __future__ import annotations

from typing import Any

from .skillspector import skillspector_execution_failure


def assess_report(report: dict[str, Any]) -> dict[str, Any]:
    issues = report.get("issues")
    risk_assessment = report.get("risk_assessment")
    metadata = report.get("metadata") or {}
    execution_failure = skillspector_execution_failure(report)
    if execution_failure:
        return {
            "risk": "Unknown",
            "reason": f"scanner_failed: {execution_failure}",
            "confidence_flags": [],
        }
    if isinstance(metadata, dict) and metadata.get("scan_error"):
        return {
            "risk": "Unknown",
            "reason": f"scanner_failed: {metadata['scan_error']}",
            "confidence_flags": [],
        }
    if not isinstance(issues, list) or not isinstance(risk_assessment, dict):
        return {
            "risk": "Unknown",
            "reason": "Scanner report did not match the expected SkillSpector shape.",
            "confidence_flags": [],
        }

    severities = {str(item.get("severity", "")).lower() for item in issues if isinstance(item, dict)}
    report_severity = str(risk_assessment.get("severity", "")).lower()
    llm_requested = bool(metadata.get("llm_requested", True))
    confidence_flags = ["Low confidence"] if not llm_requested else []

    if severities & {"critical", "high"} or report_severity in {"critical", "high"}:
        return {
            "risk": "High",
            "reason": "Critical or high severity finding detected.",
            "confidence_flags": confidence_flags,
        }
    if "medium" in severities or report_severity == "medium":
        return {"risk": "Medium", "reason": "Medium severity finding detected.", "confidence_flags": confidence_flags}
    return {
        "risk": "Low",
        "reason": "No medium, high, or critical findings detected.",
        "confidence_flags": confidence_flags,
    }
