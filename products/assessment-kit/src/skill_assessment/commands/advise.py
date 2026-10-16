import argparse
import json
import subprocess
import sys
import tempfile
from pathlib import Path

from ..adjudication import SCOPE, adjudicate_report
from ..errors import IncompleteScanError, OutputDirectoryError, ScanError, ScanTimeoutError, SkillValidationError
from .validate import validate_skill

COMMAND_ARG_NAME = "advise"
SKILL_OPTION_FLAG = "--skill"
OUTPUT_OPTION_FLAG = "--output-dir"
SCAN_MODE_OPTION_FLAG = "--scan-mode"
TIMEOUT_OPTION_FLAG = "--timeout"
ADJUDICATION_FILENAME = "adjudication.json"


def run_scanner(command: list[str], report_dir: Path, *, timeout: int = 300) -> subprocess.CompletedProcess:
    """Distinguish scanner failures from failures writing retained diagnostics."""
    try:
        with (report_dir / "scanner.log").open("w", encoding="utf-8") as log:
            try:
                return subprocess.run(command, stdout=log, stderr=subprocess.STDOUT, timeout=timeout, check=False)
            except subprocess.TimeoutExpired as exc:
                raise ScanTimeoutError(str(exc), report_dir) from exc
            except FileNotFoundError as exc:
                message = "SkillSpector is required: install it separately and ensure 'skillspector' is on PATH."
                raise ScanError(message, report_dir) from exc
            except OSError as exc:
                raise ScanError(str(exc), report_dir) from exc
    except OSError as exc:
        raise OutputDirectoryError(f"Cannot write diagnostics in {report_dir}: {exc}") from exc


def load_scanner_report(report_path: Path) -> dict:
    """Read native findings before checking execution and completeness."""
    report = json.loads(report_path.read_text(encoding="utf-8"))
    if not isinstance(report, dict) or not isinstance(report.get("issues"), list) or not all(
        isinstance(issue, dict) for issue in report["issues"]
    ):
        raise ScanError("missing or invalid findings", report_path.parent)
    return report


def validate_scan_execution(report: dict, returncode: int, report_dir: Path) -> None:
    """Reject failed execution while leaving readable findings available."""
    if returncode not in (0, 1):  # SkillSpector uses 1 for risk findings.
        raise ScanError(f"SkillSpector exited with status {returncode}", report_dir)
    if not isinstance(report.get("metadata"), dict) or not isinstance(report.get("analysis_completeness"), dict):
        raise ScanError("missing or invalid scan metadata", report_dir)
    if report.get("execution_successful") is not True:
        raise ScanError("SkillSpector execution failed", report_dir)


def validate_scan_completeness(report: dict, report_dir: Path, *, static_only: bool) -> None:
    """Enforce the requested scan mode after contextual adjudication."""
    metadata = report["metadata"]
    completeness = report["analysis_completeness"]
    if completeness.get("is_complete") is not True or metadata.get("llm_requested") is not (not static_only):
        raise IncompleteScanError("requested analysis was incomplete or changed mode", report_dir)
    if not static_only and (
        metadata.get("llm_available") is not True
        or metadata.get("llm_degraded")
        or metadata.get("llm_error")
        or metadata.get("llm_calls_attempted", 0) != metadata.get("llm_calls_succeeded", 0)
    ):
        raise IncompleteScanError("requested analysis was incomplete or degraded", report_dir)


def advise_skill(skill: Path, output_dir: Path, *, static_only: bool = False, timeout: int = 300) -> Path:
    """Validate and scan one skill, retaining native output even on failure."""
    skill = skill.resolve()
    validate_skill(skill)
    try:
        output_dir = output_dir.resolve()
        if output_dir.is_relative_to(skill):
            raise OutputDirectoryError("choose an output directory outside the skill")
        output_dir.mkdir(parents=True, exist_ok=True)
        report_dir = Path(tempfile.mkdtemp(prefix=f"{skill.name}-", dir=output_dir))
    except OSError as exc:
        raise OutputDirectoryError(f"Cannot create reports in {output_dir}: {exc}") from exc
    report_path = report_dir / "skillspector.json"
    command = ["skillspector", "scan", str(skill),
               "--format", "json", "--output", str(report_path)]
    if static_only:
        command.append("--no-llm")
    report = {}
    try:
        result = run_scanner(command, report_dir, timeout=timeout)
        report = load_scanner_report(report_path)
        validate_scan_execution(report, result.returncode, report_dir)
    except (ScanError, OSError, ValueError) as exc:
        adjudicate_report(
            report, skill / "SKILL.md", report_dir / ADJUDICATION_FILENAME, static_only=static_only,
            unavailable_reason="Scanner did not produce a usable report; findings were not adjudicated.",
        )
        if isinstance(exc, ScanError):
            raise
        raise ScanError("Cannot read the scanner report", report_dir) from exc
    # Partial coverage remains visible, but must not prevent contextual adjudication.
    adjudication = adjudicate_report(
        report, skill / "SKILL.md", report_dir / ADJUDICATION_FILENAME, timeout=timeout, static_only=static_only,
    )
    validate_scan_completeness(report, report_dir, static_only=static_only)
    if not static_only and adjudication["status"] != "completed":
        raise IncompleteScanError(f"Adjudication {adjudication['status']}", report_dir)
    return report_path


def register(subparsers) -> None:
    parser = subparsers.add_parser(COMMAND_ARG_NAME, help="Retain a scan and optional SKILL.md adjudication.")
    parser.add_argument(SKILL_OPTION_FLAG, type=Path, action="append", required=True)
    parser.add_argument(OUTPUT_OPTION_FLAG, type=Path, default=Path("assessment-reports"))
    parser.add_argument(SCAN_MODE_OPTION_FLAG, choices=("llm-assisted", "static-only"), default="llm-assisted")
    parser.add_argument(TIMEOUT_OPTION_FLAG, type=int, default=300, metavar="SECONDS",
                        help="Timeout for each scanner or adjudication request (positive integer; default: 300).")
    parser.set_defaults(handler=run, command_parser=parser)


def run(args: argparse.Namespace) -> int:
    if len(args.skill) != 1:
        args.command_parser.error(f"select exactly one {SKILL_OPTION_FLAG} directory")
    if args.timeout <= 0:
        args.command_parser.error(f"{TIMEOUT_OPTION_FLAG} must be a positive integer")
    try:
        report = advise_skill(args.skill[0], args.output_dir,
                              static_only=args.scan_mode == "static-only", timeout=args.timeout)
    except ScanError as exc:
        print(str(exc), file=sys.stderr)
        show_reports(exc.report_dir)
        return 3
    except (OSError, UnicodeError, SkillValidationError, OutputDirectoryError) as exc:
        print(str(exc), file=sys.stderr)
        return 1
    show_reports(report.parent)
    return 0


def show_reports(report_dir: Path) -> None:
    for name in ("skillspector.json", ADJUDICATION_FILENAME):
        path = report_dir / name
        if path.exists():
            print(f"{'Adjudication' if name == ADJUDICATION_FILENAME else 'Advice report'}: {path}")
    if (report_dir / ADJUDICATION_FILENAME).exists():
        print(SCOPE)
