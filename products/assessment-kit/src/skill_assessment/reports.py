"""The native report fields needed to assess findings and retain matching evidence."""

import json
from pathlib import Path

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
