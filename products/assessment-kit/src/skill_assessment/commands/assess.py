import hashlib
import json
import sys
from datetime import UTC, datetime
from pathlib import Path

from ..errors import OutputDirectoryError, ScanError
from .advise import advise_skill, show_reports


def skill_digest(skill: Path) -> str:
    digest = hashlib.sha256(b"skill-assessment-package-v1\0")
    files = (path for path in skill.rglob("*") if path.is_file())
    for path in sorted(files, key=lambda path: path.relative_to(skill).as_posix()):
        for value in (path.relative_to(skill).as_posix().encode("utf-8"), path.read_bytes()):
            digest.update(len(value).to_bytes(8, "big"))
            digest.update(value)
    return digest.hexdigest()


def assess_skill(
    skill: Path, output_dir: Path, *, static_only: bool = False, timeout: int = 300, override: bool = False,
) -> Path:
    """Run advise and record one assessment per skill content hash."""
    skill, output_dir = skill.resolve(), output_dir.resolve()
    digest = skill_digest(skill)
    index_path = output_dir / "index.json"
    index = json.loads(index_path.read_text(encoding="utf-8")) if index_path.exists() else {
        "boe_schema_version": 1, "skill": skill.name, "assessments": [],
    }
    existing = next((entry for entry in index["assessments"] if entry["skill_sha256"] == digest), None)
    if existing is not None and not override:
        raise ValueError(f"Assessment already exists at {output_dir / existing['path']}; use --override to replace it")
    report = advise_skill(skill, output_dir, static_only=static_only, timeout=timeout)
    assessment = report.parent
    if existing is not None:
        assessment = output_dir / existing["path"]
        assessment.mkdir(parents=True, exist_ok=True)
        for path in report.parent.iterdir():
            path.replace(assessment / path.name)
        report.parent.rmdir()
        index["assessments"].remove(existing)
    index["assessments"].insert(0, {
        "assessed_at": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
        "path": existing["path"] if existing is not None else assessment.name,
        "skill_sha256": digest,
        "reports": {name: hashlib.sha256((assessment / name).read_bytes()).hexdigest()
                    for name in ("skillspector.json", "adjudication.json", "scanner.log")},
    })
    index_path.write_text(json.dumps(index, indent=2) + "\n", encoding="utf-8")
    return assessment


def register(subparsers) -> None:
    parser = subparsers.add_parser("assess", help="Run advise and update one skill's BOE index.")
    parser.add_argument("--skill", type=Path, action="append", required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--scan-mode", choices=("llm-assisted", "static-only"), default="llm-assisted")
    parser.add_argument("--override", action="store_true", help="Replace the assessment for unchanged skill contents.")
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
                                  override=args.override)
    except ScanError as exc:
        print(str(exc), file=sys.stderr)
        show_reports(exc.report_dir)
        return 3
    except (OSError, ValueError, KeyError, TypeError, AttributeError, OutputDirectoryError) as exc:
        print(str(exc), file=sys.stderr)
        return 1
    show_reports(assessment)
    print(f"BOE index: {args.output_dir.resolve() / 'index.json'}")
    return 0
