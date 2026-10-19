import hashlib
import json
import sys
from pathlib import Path

from ..errors import SkillValidationError
from .assess import skill_digest
from .validate import validate_skill


def verify_boe(skill: Path, boe_dir: Path) -> dict:
    validate_skill(skill)
    root = boe_dir.resolve()
    index = json.loads((root / "index.json").read_text(encoding="utf-8"))
    if index["boe_schema_version"] != 1 or index["skill"] != skill.name:
        raise ValueError("Unsupported BOE index or mismatched skill")
    digest = skill_digest(skill)
    entries = [entry for entry in index["assessments"] if entry["skill_sha256"] == digest]
    if len(entries) != 1:
        raise ValueError("Expected exactly one assessment for current skill contents")
    entry = entries[0]
    directory = (root / entry["path"]).resolve()
    if Path(entry["path"]).is_absolute() or not directory.is_relative_to(root) or directory == root:
        raise ValueError("Assessment path must stay inside the BOE directory")
    if set(entry["reports"]) != {"skillspector.json", "adjudication.json", "scanner.log"}:
        raise ValueError("BOE must record all three report digests; reassess older evidence explicitly")
    for name, expected in entry["reports"].items():
        report = directory / name
        if not report.resolve().is_relative_to(directory):
            raise ValueError(f"Report escapes assessment directory: {name}")
        if hashlib.sha256(report.read_bytes()).hexdigest() != expected:
            raise ValueError(f"Report digest mismatch: {name}")
    return entry


def register(subparsers) -> None:
    parser = subparsers.add_parser("verify-boe", help="Verify skill content and retained report digests offline.")
    parser.add_argument("--skill", type=Path, required=True)
    parser.add_argument("--boe-dir", type=Path, required=True)
    parser.set_defaults(handler=run)


def run(args) -> int:
    try:
        entry = verify_boe(args.skill, args.boe_dir)
    except (OSError, ValueError, KeyError, TypeError, AttributeError, SkillValidationError) as exc:
        print(f"Invalid BOE: {exc}", file=sys.stderr)
        return 1
    print(json.dumps(entry))
    return 0
