"""Run the installed assessment CLI and build the operator's catalog from its assessment output."""

import argparse
import json
import subprocess
from datetime import datetime
from pathlib import Path

from .exchange_builder import build_exchange, is_successful_skillspector_report, make_scan_key, scan_mode
from .skills import discover_skills


def read_assessment_boe(*, boe_dir, skill, mode):
    directory = boe_dir / skill.metadata.namespace / skill.metadata.skill_id
    # Assess prepends its successful run; generation consumes that job's latest output.
    index = json.loads((directory / "index.json").read_text(encoding="utf-8"))
    entry = index["assessments"][0]
    report_path = directory / entry["path"] / "skillspector.json"
    report = json.loads(report_path.read_text(encoding="utf-8"))
    if not is_successful_skillspector_report(report) or scan_mode(report) != mode:
        raise ValueError(f"Incomplete assessment or wrong scan mode: {skill.metadata.display_id}")
    if datetime.fromisoformat(entry["assessed_at"]).tzinfo is None:
        raise ValueError("Assessment timestamp requires a timezone")
    metadata = report["metadata"]
    config = {"native_output_format": "skillspector-json-v2", "scan_mode": mode}
    if mode == "llm-assisted":
        config.update(llm_provider=metadata.get("llm_provider"), llm_model=metadata.get("llm_model"))
    version = metadata["skillspector_version"]
    return {
        "report": report, "report_path": report_path, "boe_path": directory / "index.json",
        "scan_timestamp": entry["assessed_at"], "scanner_version": version, "scanner_config": config,
        "scan_key": make_scan_key(namespace=skill.metadata.namespace, skill_id=skill.metadata.skill_id,
                                  content_hash=skill.content_hash, scanner_version=version,
                                  mode=mode, scanner_config=config),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("advise", "assess", "generate"))
    parser.add_argument("--skills", type=Path, default=Path("skills"))
    parser.add_argument("--evidence", type=Path, default=Path("evidence"))
    parser.add_argument("--policy", type=Path, default=Path(".exchange"))
    parser.add_argument("--generated", type=Path, default=Path(".exchange/generated"))
    parser.add_argument("--scan-mode", choices=("static-only", "llm-assisted"), default="llm-assisted")
    parser.add_argument("--override", action="store_true")
    args = parser.parse_args()
    if args.override and args.command != "assess":
        parser.error("--override is only valid for assess")
    skills = discover_skills(args.skills)
    if not skills:
        parser.error("No skills found: expected <skills>/<namespace>/<skill>/SKILL.md")
    if args.command != "generate":
        for skill in skills:
            output = args.evidence / skill.metadata.namespace / skill.metadata.skill_id
            command = ["skill-assessment", args.command, "--skill", str(skill.path),
                       "--output-dir", str(output), "--scan-mode", args.scan_mode]
            if args.override:
                command.append("--override")
            subprocess.run(command, check=True)
    if args.command == "generate":
        result = build_exchange(skills_root=args.skills, exchange_dir=args.policy,
                                generated_dir=args.generated, scan_modes=(args.scan_mode,),
                                boe_dir=args.evidence, boe_reader=read_assessment_boe)
        if result["skills_written"] != len(skills):
            raise ValueError(f"Not all selected skills were generated: {result}")
        print(json.dumps(result))


if __name__ == "__main__":
    main()
