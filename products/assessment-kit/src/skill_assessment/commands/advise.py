import argparse
import json
import subprocess
import sys
import tempfile
from pathlib import Path

from ..errors import IncompleteScanError, InvalidOutputDirectoryError, ScanError, SkillValidationError
from .validate import validate_skill

COMMAND_ARG_NAME = "advise"
SKILL_OPTION_FLAG = "--skill"
OUTPUT_OPTION_FLAG = "--output-dir"
SCAN_MODE_OPTION_FLAG = "--scan-mode"


def advise_skill(skill: Path, output_dir: Path, *, static_only: bool = False) -> Path:
    """Validate and scan one skill, retaining native output even on failure."""
    skill, output_dir = skill.resolve(), output_dir.resolve()
    validate_skill(skill)
    if output_dir.is_relative_to(skill):
        raise InvalidOutputDirectoryError("choose an output directory outside the skill")
    output_dir.mkdir(parents=True, exist_ok=True)
    report_dir = Path(tempfile.mkdtemp(prefix=f"{skill.name}-", dir=output_dir))
    report_path = report_dir / "skillspector.json"
    command = ["skillspector", "scan", str(skill),
               "--format", "json", "--output", str(report_path)]
    if static_only:
        command.append("--no-llm")
    try:
        with (report_dir / "scanner.log").open("w", encoding="utf-8") as log:
            try:
                result = subprocess.run(command, stdout=log, stderr=subprocess.STDOUT, timeout=300, check=False)
            except FileNotFoundError as exc:
                message = "SkillSpector is required: install it separately and ensure 'skillspector' is on PATH."
                log.write(message + "\n")
                raise ScanError(message, report_dir) from exc
        if result.returncode not in (0, 1):  # SkillSpector uses 1 for risk findings.
            raise ScanError(f"SkillSpector exited with status {result.returncode}", report_dir)
        report = json.loads(report_path.read_text(encoding="utf-8"))
    except (OSError, ValueError, subprocess.TimeoutExpired) as exc:
        raise ScanError(str(exc), report_dir) from exc
    if not isinstance(report, dict) or not isinstance(report.get("issues"), list):
        raise ScanError("missing or invalid findings", report_dir)
    metadata = report.get("metadata")
    completeness = report.get("analysis_completeness")
    if not isinstance(metadata, dict) or not isinstance(completeness, dict):
        raise ScanError("missing or invalid scan metadata", report_dir)
    if report.get("execution_successful") is not True:
        raise ScanError("SkillSpector execution failed", report_dir)
    if completeness.get("is_complete") is not True or metadata.get("llm_requested") is not (not static_only):
        raise IncompleteScanError("requested analysis was incomplete or changed mode", report_dir)
    if not static_only and (
        metadata.get("llm_available") is not True
        or metadata.get("llm_degraded")
        or metadata.get("llm_error")
        or metadata.get("llm_calls_attempted", 0) != metadata.get("llm_calls_succeeded", 0)
    ):
        raise IncompleteScanError("requested analysis was incomplete or degraded", report_dir)
    return report_path


def register(subparsers) -> None:
    parser = subparsers.add_parser(COMMAND_ARG_NAME, help="Retain SkillSpector advice for one skill.")
    parser.add_argument(SKILL_OPTION_FLAG, type=Path, action="append", required=True)
    parser.add_argument(OUTPUT_OPTION_FLAG, type=Path, default=Path("assessment-reports"))
    parser.add_argument(SCAN_MODE_OPTION_FLAG, choices=("llm-assisted", "static-only"), default="llm-assisted")
    parser.set_defaults(handler=run, command_parser=parser)


def run(args: argparse.Namespace) -> int:
    if len(args.skill) != 1:
        args.command_parser.error(f"select exactly one {SKILL_OPTION_FLAG} directory")
    try:
        report = advise_skill(args.skill[0], args.output_dir, static_only=args.scan_mode == "static-only")
    except ScanError as exc:
        print(str(exc), file=sys.stderr)
        return 3
    except (OSError, UnicodeError, SkillValidationError, InvalidOutputDirectoryError) as exc:
        print(str(exc), file=sys.stderr)
        return 1
    print(f"Advice report: {report}")
    return 0
