import json
import os
import sys
from datetime import datetime
from pathlib import Path

from ..adjudication import validate_verdict
from ..errors import OutputDirectoryError, ScanError
from ..hashing import skill_digest
from ..reports import load_scanner_report, validate_assessment_report
from ..scanning import (
    require_scanner,
    scan_skill,
    show_reports,
    strip_source_base,
)
from .validate import validate_skill


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


def assess_skill(
    skill: Path, output_dir: Path, *, static_only: bool = False, timeout: int = 300, if_changed: bool = False,
    base_dir: Path | None = None,
) -> Path:
    """Replace the current reports only after a successful staged assessment."""
    require_scanner()
    skill, output_dir = skill.resolve(), output_dir.resolve()
    validate_skill(skill)
    if output_dir.is_relative_to(skill):
        raise OutputDirectoryError("choose an output directory outside the skill")
    digest = skill_digest(skill)
    if if_changed and is_current_assessment(output_dir, digest, static_only=static_only):
        if base_dir is not None:
            strip_source_base(output_dir / "skillspector.json", base_dir)
        return output_dir
    # Scanning creates a unique sibling directory, keeping failed scans out of current output.
    report = scan_skill(skill, output_dir.parent, static_only=static_only, timeout=timeout, base_dir=base_dir)
    adjudication_path = report.with_name("adjudication.json")
    adjudication = json.loads(adjudication_path.read_text(encoding="utf-8"))
    adjudication["skill_sha256"] = digest
    adjudication_path.write_text(json.dumps(adjudication, indent=2) + "\n", encoding="utf-8")
    output_dir.mkdir(parents=True, exist_ok=True)
    for name in ("skillspector.json", "adjudication.json", "scanner.log"):
        (report.parent / name).replace(output_dir / name)
    report.parent.rmdir()
    return output_dir


def register(subparsers) -> None:
    parser = subparsers.add_parser("assess", help="Scan one skill and retain its current reports.")
    parser.add_argument("--skill", type=Path, action="append", required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--base-dir", type=Path, default=os.environ.get("SKILL_ASSESSMENT_BASE_DIR"),
                        help="Strip the native source prefix (default: SKILL_ASSESSMENT_BASE_DIR).")
    parser.add_argument("--scan-mode", choices=("llm-assisted", "static-only"), default="llm-assisted")
    parser.add_argument("--if-changed", action="store_true", help="Skip matching successful reports in this scan mode.")
    parser.add_argument("--timeout", type=int, default=300, metavar="SECONDS",
                        help="Timeout for each scanner or adjudication request (positive integer; default: 300).")
    parser.set_defaults(handler=run, command_parser=parser)


def run(args) -> int:
    if len(args.skill) != 1:
        args.command_parser.error("select exactly one --skill directory")
    if args.timeout <= 0:
        args.command_parser.error("--timeout must be a positive integer")
    try:
        assessment = assess_skill(args.skill[0], args.output_dir,
                                  static_only=args.scan_mode == "static-only", timeout=args.timeout,
                                  if_changed=args.if_changed, base_dir=args.base_dir)
    except ScanError as exc:
        print(str(exc), file=sys.stderr)
        if exc.report_dir is not None:
            show_reports(exc.report_dir)
        return 3
    except (OSError, ValueError, KeyError, TypeError, AttributeError, OutputDirectoryError) as exc:
        print(str(exc), file=sys.stderr)
        return 1
    show_reports(assessment)
    return 0
