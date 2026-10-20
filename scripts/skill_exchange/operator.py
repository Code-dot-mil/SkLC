"""Run the installed assessment CLI and build the operator's catalog from its assessment output."""

import argparse
import json
import subprocess
from datetime import datetime
from pathlib import Path

from skill_assessment.reports import validate_assessment_report

from .exchange_builder import build_exchange, make_scan_key, scan_mode
from .skills import discover_skills


def read_assessment_boe(*, boe_dir, skill, mode):
    directory = boe_dir / skill.metadata.namespace / skill.metadata.skill_id
    adjudication_path = directory / "adjudication.json"
    adjudication = json.loads(adjudication_path.read_text(encoding="utf-8"))
    assessed_at = adjudication["metadata"]["created_at"]
    report_path = directory / "skillspector.json"
    report = json.loads(report_path.read_text(encoding="utf-8"))
    validate_assessment_report(report, directory, static_only=mode == "static-only")
    if scan_mode(report) != mode:
        raise ValueError(f"Wrong scan mode: {skill.metadata.display_id}")
    if datetime.fromisoformat(assessed_at).tzinfo is None:
        raise ValueError("Assessment timestamp requires a timezone")
    metadata = report["metadata"]
    config = {"native_output_format": "skillspector-json-v2", "scan_mode": mode}
    if mode == "llm-assisted":
        config.update(llm_provider=metadata.get("llm_provider"), llm_model=metadata.get("llm_model"))
    version = metadata["skillspector_version"]
    return {
        "report": report, "report_path": report_path, "boe_path": adjudication_path,
        "scan_timestamp": assessed_at, "scanner_version": version, "scanner_config": config,
        "scan_key": make_scan_key(namespace=skill.metadata.namespace, skill_id=skill.metadata.skill_id,
                                  content_hash=skill.content_hash, scanner_version=version,
                                  mode=mode, scanner_config=config),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("assess", "generate"))
    parser.add_argument("--skills", type=Path, default=Path("skills"))
    parser.add_argument("--evidence", type=Path, default=Path("evidence"))
    parser.add_argument("--policy", type=Path, default=Path(".exchange"))
    parser.add_argument("--generated", type=Path, default=Path(".exchange/generated"))
    parser.add_argument("--scan-mode", choices=("static-only", "llm-assisted"), default="llm-assisted")
    parser.add_argument("--if-changed", action="store_true")
    args = parser.parse_args()
    if args.if_changed and args.command != "assess":
        parser.error("--if-changed is only valid for assess")
    if args.command != "generate":
        skills = discover_skills(args.skills)
        if not skills:
            parser.error("No skills found: expected <skills>/<namespace>/<skill>/SKILL.md")
        for skill in skills:
            output = args.evidence / skill.metadata.namespace / skill.metadata.skill_id
            command = ["skill-assessment", args.command, "--skill", str(skill.path),
                       "--output-dir", str(output), "--scan-mode", args.scan_mode]
            if args.if_changed:
                command.append("--if-changed")
            subprocess.run(command, check=True)
            with (output / "assessment.md").open("w", encoding="utf-8") as summary:
                subprocess.run(["skill-assessment", "summarize", "--assessment-dir", str(output)],
                               stdout=summary, check=True)
    if args.command == "generate":
        result = build_exchange(skills_root=args.skills, exchange_dir=args.policy,
                                generated_dir=args.generated, scan_modes=(args.scan_mode,),
                                boe_dir=args.evidence, boe_reader=read_assessment_boe)
        if not result["skills_written"] or result["invalid_skills"]:
            raise ValueError(f"Catalog is empty or contains invalid skills: {result}")
        print(json.dumps(result))


if __name__ == "__main__":
    main()
