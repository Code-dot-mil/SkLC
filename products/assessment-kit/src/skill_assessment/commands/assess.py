import json
import os
import sys
from pathlib import Path

from ..adjudication import SCOPE
from ..defaults import DEFAULT_MAX_COMPLETION_TOKENS, DEFAULT_TIMEOUT_SECONDS
from ..errors import OutputDirectoryError, ScanError, WorkflowTimeoutError
from ..hashing import skill_digest
from ..reports import is_current_assessment
from ..scanning import (
    WORKFLOW_TIMEOUT_ENV,
    require_scanner,
    scan_skill,
    show_reports,
    strip_source_base,
    workflow_timeout,
)
from .validate import validate_skill

SKILL_FLAG = "--skill"
TIMEOUT_FLAG = "--timeout"
MAX_COMPLETION_TOKENS_FLAG = "--max-completion-tokens"
BASE_DIR_ENV = "SKILL_ASSESSMENT_BASE_DIR"


def assess_skill(
    skill: Path, output_dir: Path, *, static_only: bool = False, timeout: int = DEFAULT_TIMEOUT_SECONDS,
    if_changed: bool = False,
    base_dir: Path | None = None, max_completion_tokens: int = DEFAULT_MAX_COMPLETION_TOKENS,
) -> Path:
    """Replace the current reports only after a successful staged assessment."""
    if timeout <= 0 or max_completion_tokens <= 0:
        raise ValueError("Timeout and max completion tokens must be positive.")
    require_scanner()
    skill, output_dir = skill.resolve(), output_dir.resolve()
    validate_skill(skill)
    if output_dir.is_relative_to(skill):
        raise OutputDirectoryError("choose an output directory outside the skill")
    digest = skill_digest(skill)
    current = if_changed and is_current_assessment(output_dir, digest, static_only=static_only)
    if current and not static_only:
        current = json.loads((output_dir / "adjudication.json").read_text())["scope"] == SCOPE
    if current:
        if base_dir is not None:
            strip_source_base(output_dir / "skillspector.json", base_dir)
        return output_dir
    # Scanning creates a unique sibling directory, keeping failed scans out of current output.
    report = scan_skill(skill, output_dir.parent, static_only=static_only, timeout=timeout, base_dir=base_dir,
                        max_completion_tokens=max_completion_tokens)
    if skill_digest(skill) != digest:
        raise ScanError("Skill changed during assessment; reports were not promoted.", report.parent)
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
    parser.add_argument(SKILL_FLAG, dest="skill", type=Path, action="append", required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--base-dir", type=Path, default=os.environ.get(BASE_DIR_ENV),
                        help=f"Strip the native source prefix (default: {BASE_DIR_ENV}).")
    parser.add_argument("--scan-mode", choices=("llm-assisted", "static-only"), default="llm-assisted")
    parser.add_argument("--if-changed", action="store_true", help="Skip matching successful reports in this scan mode.")
    parser.add_argument(TIMEOUT_FLAG, dest="timeout", type=int, default=DEFAULT_TIMEOUT_SECONDS, metavar="SECONDS",
                        help=f"Timeout for each scanner or adjudication request (default: {DEFAULT_TIMEOUT_SECONDS}).")
    parser.add_argument(MAX_COMPLETION_TOKENS_FLAG, dest="max_completion_tokens", type=int,
                        default=DEFAULT_MAX_COMPLETION_TOKENS,
                        help=f"Adjudication output allowance, including reasoning "
                             f"(default: {DEFAULT_MAX_COMPLETION_TOKENS}).")
    parser.set_defaults(handler=run, command_parser=parser)


def run(args) -> int:
    if len(args.skill) != 1:
        args.command_parser.error(f"select exactly one {SKILL_FLAG} directory")
    if args.timeout <= 0:
        args.command_parser.error(f"{TIMEOUT_FLAG} must be a positive integer")
    if args.max_completion_tokens <= 0:
        args.command_parser.error(f"{MAX_COMPLETION_TOKENS_FLAG} must be a positive integer")
    try:
        assessment = assess_skill(args.skill[0], args.output_dir,
                                  static_only=args.scan_mode == "static-only", timeout=args.timeout,
                                  if_changed=args.if_changed, base_dir=args.base_dir,
                                  max_completion_tokens=args.max_completion_tokens)
    except ScanError as exc:
        print(str(exc), file=sys.stderr)
        if isinstance(exc, WorkflowTimeoutError):
            print(f"Configured scanner workflow limit: {workflow_timeout(args.timeout)} seconds. "
                  f"Retry with a larger {TIMEOUT_FLAG}, for example {TIMEOUT_FLAG} {args.timeout * 2}. "
                  f"If {WORKFLOW_TIMEOUT_ENV} is explicitly set, increase it too.", file=sys.stderr)
        if exc.report_dir is not None:
            show_reports(exc.report_dir)
        return 3
    except (OSError, ValueError, KeyError, TypeError, AttributeError, OutputDirectoryError) as exc:
        print(str(exc), file=sys.stderr)
        return 1
    show_reports(assessment)
    return 0
