import json
import shutil
import subprocess
import tempfile
from pathlib import Path

from .adjudication import DEFAULT_ENFORCE_COVERAGE, SCOPE, adjudicate_report
from .commands.validate import validate_skill
from .errors import IncompleteScanError, OutputDirectoryError, ScanError, ScanTimeoutError
from .reports import load_scanner_report, validate_assessment_report, validate_scan_execution

ADJUDICATION_FILENAME = "adjudication.json"
SCANNER_REQUIRED = "SkillSpector is required: install it separately and ensure 'skillspector' is on PATH."


def require_scanner() -> None:
    """Check the external prerequisite before creating or reusing reports."""
    if shutil.which("skillspector") is None:
        raise ScanError(SCANNER_REQUIRED)


def strip_source_base(report_path: Path, base_dir: Path) -> None:
    """Rewrite only matching native skill.source paths; leave other evidence intact."""
    report = json.loads(report_path.read_text(encoding="utf-8"))
    skill = report.get("skill") if isinstance(report, dict) else None
    source = skill.get("source") if isinstance(skill, dict) else None
    if not isinstance(source, str) or not Path(source).is_absolute():
        return
    try:
        relative = Path(source).resolve().relative_to(base_dir.resolve())
    except ValueError:
        return
    skill["source"] = str(relative)
    report_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")


def run_scanner(command: list[str], report_dir: Path, *, timeout: int = 300) -> subprocess.CompletedProcess:
    """Distinguish scanner failures from failures writing retained diagnostics."""
    try:
        with (report_dir / "scanner.log").open("w", encoding="utf-8") as log:
            try:
                return subprocess.run(command, stdout=log, stderr=subprocess.STDOUT, timeout=timeout, check=False)
            except subprocess.TimeoutExpired as exc:
                raise ScanTimeoutError(str(exc), report_dir) from exc
            except FileNotFoundError as exc:
                raise ScanError(SCANNER_REQUIRED, report_dir) from exc
            except OSError as exc:
                raise ScanError(str(exc), report_dir) from exc
    except OSError as exc:
        raise OutputDirectoryError(f"Cannot write diagnostics in {report_dir}: {exc}") from exc


def scan_skill(
    skill: Path, output_dir: Path, *, static_only: bool = False, timeout: int = 300, base_dir: Path | None = None,
    enforce_coverage: bool = DEFAULT_ENFORCE_COVERAGE,
) -> Path:
    """Validate and scan one skill, retaining native output even on failure."""
    require_scanner()
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
        if base_dir is not None:
            strip_source_base(report_path, base_dir)
        report = load_scanner_report(report_path)
        validate_scan_execution(report, result.returncode, report_dir)
    except (ScanError, OSError, ValueError) as exc:
        if isinstance(exc, ScanError) and base_dir is not None and report_path.is_file():
            try:
                strip_source_base(report_path, base_dir)
            except (OSError, ValueError):
                exc = type(exc)(f"{exc}; source prefix could not be stripped", report_dir)
        adjudicate_report(
            report, skill / "SKILL.md", report_dir / ADJUDICATION_FILENAME, static_only=static_only,
            unavailable_reason="Scanner did not produce a usable report; findings were not adjudicated.",
            enforce_coverage=enforce_coverage,
        )
        if isinstance(exc, ScanError):
            raise exc
        raise ScanError("Cannot read the scanner report", report_dir) from exc
    # Always adjudicate available findings; the requested policy controls the coverage verdict.
    adjudication = adjudicate_report(
        report, skill / "SKILL.md", report_dir / ADJUDICATION_FILENAME, timeout=timeout, static_only=static_only,
        enforce_coverage=enforce_coverage,
    )
    validate_assessment_report(report, report_dir, static_only=static_only)
    if not static_only and adjudication["status"] != "completed":
        raise IncompleteScanError(f"Adjudication {adjudication['status']}", report_dir)
    return report_path


def show_reports(report_dir: Path) -> None:
    for name in ("skillspector.json", ADJUDICATION_FILENAME):
        path = report_dir / name
        if path.exists():
            print(f"{'Adjudication' if name == ADJUDICATION_FILENAME else 'Scanner report'}: {path}")
    if (report_dir / ADJUDICATION_FILENAME).exists():
        print(SCOPE)
