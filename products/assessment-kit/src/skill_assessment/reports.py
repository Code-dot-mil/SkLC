"""The native report fields needed to assess findings and retain matching evidence."""

import json
from datetime import datetime
from pathlib import Path

from .adjudication import validate_verdict
from .errors import IncompleteScanError, ScanError


def load_scanner_report(report_path: Path) -> dict:
    """Read the native findings used by adjudication and summaries."""
    report = json.loads(report_path.read_text(encoding="utf-8"))
    if not isinstance(report, dict) or not isinstance(report.get("issues"), list) or not all(
        isinstance(issue, dict) for issue in report["issues"]
    ):
        raise ScanError("missing or invalid findings", report_path.parent)
    return report


def validate_scan_execution(report: dict, returncode: int, report_dir: Path) -> None:
    """Reject failed execution while leaving readable findings available."""
    if returncode not in (0, 1):  # SkillSpector uses 1 for risk findings, 2 for execution failures.
        raise ScanError(f"SkillSpector exited with status {returncode}", report_dir)
    if not isinstance(report.get("metadata"), dict):
        raise ScanError("missing or invalid scan metadata", report_dir)
    if report.get("execution_successful") is not True:
        raise ScanError("SkillSpector execution failed", report_dir)


def validate_requested_mode(report: dict, report_dir: Path, *, static_only: bool) -> None:
    """Reject changed scan mode and failed or degraded requested inference."""
    metadata = report["metadata"]
    if metadata.get("llm_requested") is not (not static_only):
        raise IncompleteScanError("requested analysis changed mode", report_dir)
    if not static_only and (
        metadata.get("llm_available") is not True
        or metadata.get("llm_degraded")
        or metadata.get("llm_error")
        or metadata.get("llm_calls_attempted", 0) != metadata.get("llm_calls_succeeded", 0)
    ):
        raise IncompleteScanError("requested analysis was incomplete or degraded", report_dir)


def validate_assessment_report(report: dict, report_dir: Path, *, static_only: bool) -> None:
    """Use the scanner's execution outcome; coverage details remain native evidence."""
    validate_scan_execution(report, 0, report_dir)
    validate_requested_mode(report, report_dir, static_only=static_only)


def is_current_assessment(output_dir: Path, digest: str, *, static_only: bool) -> bool:
    """Only reuse a successful assessment of these bytes in this mode."""
    try:
        report = load_scanner_report(output_dir / "skillspector.json")
        validate_assessment_report(report, output_dir, static_only=static_only)
        adjudication = json.loads((output_dir / "adjudication.json").read_text(encoding="utf-8"))
        timestamp = datetime.fromisoformat(adjudication["metadata"]["created_at"])
        if timestamp.tzinfo is None:
            return False
        for key in ("summary", "coverage_reason", "scope"):
            if not isinstance(adjudication[key], str) or not adjudication[key].strip():
                return False
        if static_only:
            if adjudication["safe_to_use"] is not None or adjudication["coverage_sufficient"] is not None:
                return False
            findings = adjudication["findings"]
            if not isinstance(findings, list) or len(findings) != len(report["issues"]):
                return False
            for index, (finding, issue) in enumerate(zip(findings, report["issues"], strict=True), 1):
                if (finding["index"] != index or finding["rule_id"] != issue.get("id", issue.get("rule_id"))
                        or finding["determination"] != "not_adjudicated"
                        or not isinstance(finding["reason"], str) or not finding["reason"].strip()):
                    return False
        else:
            validate_verdict({key: adjudication[key] for key in (
                "safe_to_use", "summary", "coverage_sufficient", "coverage_reason", "findings",
            )}, report["issues"])
        return (
            adjudication.get("skill_sha256") == digest
            and adjudication.get("status") == ("not_performed" if static_only else "completed")
        )
    except (OSError, ValueError, KeyError, TypeError, AttributeError, ScanError):
        # Missing, malformed, or failed reports require a new scan, never a skip.
        return False
