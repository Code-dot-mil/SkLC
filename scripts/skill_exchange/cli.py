from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

from .exchange_builder import build_exchange
from .git_mock import append_event
from .policy import load_exchange_policy
from .risk import assess_report
from .skills import discover_skills
from .skillspector import load_fixture_report, run_skillspector
from .validation import validate_skill


def main() -> None:
    parser = argparse.ArgumentParser()
    subcommands = parser.add_subparsers(dest="command", required=True)

    scan = subcommands.add_parser("mock-mr-scan")
    scan.add_argument("--mr", required=True)
    scan.add_argument("--scanner", choices=["fixture", "real"], default="fixture")
    scan.add_argument("--fixture", default="skillspector-clean.json")
    scan.add_argument("--no-llm", action="store_true", default=True)

    publish = subcommands.add_parser("publish-local")
    publish.add_argument("--scanner", choices=["fixture", "real"], default="fixture")
    publish.add_argument("--fixture", default="skillspector-clean.json")

    args = parser.parse_args()
    if args.command == "mock-mr-scan":
        mock_mr_scan(args)
    if args.command == "publish-local":
        result = build_exchange(
            skills_root=Path("skills"),
            exchange_dir=Path(".exchange"),
            generated_dir=Path(".exchange/generated"),
            scanner=args.scanner,
            fixture=args.fixture,
        )
        print(json.dumps(result, indent=2, sort_keys=True))


def mock_mr_scan(args: argparse.Namespace) -> None:
    run_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    mr_log = Path(".gitlab-mock/mr") / f"{args.mr}.md.jsonl"
    artifact_root = Path(".gitlab-mock/mr-artifacts") / args.mr / run_id
    policy = load_exchange_policy(Path(".exchange"))
    skills = discover_skills(Path("skills"))

    append_event(mr_log, {"type": "pipeline.started", "mr_id": args.mr, "run_id": run_id})

    validation_rows = []
    summary_rows = []
    for skill in skills:
        validation = validate_skill(skill, policy)
        report_path = artifact_root / "skillspector" / skill.metadata.namespace / skill.metadata.skill_id / "report.json"
        if args.scanner == "fixture":
            report = load_fixture_report(args.fixture)
            report_path.parent.mkdir(parents=True, exist_ok=True)
            report_path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
        else:
            report = run_skillspector(skill.path, report_path, no_llm=args.no_llm)
        assessment = assess_report(report)
        validation_rows.append(
            {
                "skill": skill.metadata.display_id,
                "errors": list(validation.errors),
                "warnings": list(validation.warnings),
                "metadata_flags": list(validation.metadata_flags),
            }
        )
        summary_rows.append(
            {
                "skill": skill.metadata.display_id,
                "risk": assessment["risk"],
                "reason": assessment["reason"],
                "confidence_flags": assessment["confidence_flags"],
                "report": str(report_path),
            }
        )

    artifact_root.mkdir(parents=True, exist_ok=True)
    (artifact_root / "validation.json").write_text(json.dumps(validation_rows, indent=2, sort_keys=True) + "\n")
    (artifact_root / "changed-skills.json").write_text(json.dumps(summary_rows, indent=2, sort_keys=True) + "\n")
    comment_path = artifact_root / "comment.md"
    comment_path.write_text(render_comment(summary_rows, validation_rows))

    append_event(mr_log, {"type": "validation.completed", "mr_id": args.mr, "artifact": str(artifact_root / "validation.json")})
    append_event(mr_log, {"type": "skillspector.completed", "mr_id": args.mr, "artifact": str(artifact_root / "changed-skills.json")})
    append_event(mr_log, {"type": "comment.created", "mr_id": args.mr, "path": str(comment_path)})
    append_event(mr_log, {"type": "pipeline.completed", "mr_id": args.mr, "status": "success"})


def render_comment(summary_rows: list[dict], validation_rows: list[dict]) -> str:
    lines = ["# SkillSpector Review", "", "| Skill | Risk | Flags | Reason |", "|---|---|---|---|"]
    for row in summary_rows:
        flags = ", ".join(row["confidence_flags"]) if row["confidence_flags"] else "-"
        lines.append(f"| `{row['skill']}` | {row['risk']} | {flags} | {row['reason']} |")
    lines.append("")
    lines.append("## Validation")
    for row in validation_rows:
        warnings = ", ".join(row["warnings"]) if row["warnings"] else "none"
        flags = ", ".join(row["metadata_flags"]) if row["metadata_flags"] else "none"
        lines.append(f"- `{row['skill']}` warnings: {warnings}; metadata flags: {flags}")
    return "\n".join(lines) + "\n"


if __name__ == "__main__":
    main()
