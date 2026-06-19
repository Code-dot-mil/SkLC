from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .boe import write_boe
from .policy import load_exchange_policy
from .risk import assess_report
from .skills import discover_skills
from .skillspector import load_fixture_report, run_skillspector
from .validation import validate_skill
from .zipper import write_skill_zip


def build_exchange(
    *,
    skills_root: Path,
    exchange_dir: Path,
    generated_dir: Path,
    scanner: str,
    fixture: str,
) -> dict[str, Any]:
    generated_dir.mkdir(parents=True, exist_ok=True)
    policy = load_exchange_policy(exchange_dir)
    skills = discover_skills(skills_root)
    records: list[dict[str, Any]] = []
    reused_scans = 0

    for skill in skills:
        validation = validate_skill(skill, policy)
        report_source = generated_dir / "tmp" / skill.metadata.namespace / skill.metadata.skill_id / "report.json"
        if scanner == "fixture":
            report = load_fixture_report(fixture)
            report_source.parent.mkdir(parents=True, exist_ok=True)
            report_source.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
        else:
            report = run_skillspector(skill.path, report_source, no_llm=True)

        scan_key = make_scan_key(skill.content_hash, report)
        existing_boe_path = boe_path_for(generated_dir, skill, scan_key)
        if existing_boe_path.exists():
            assessment = assessment_from_boe(existing_boe_path)
            boe_path = existing_boe_path
            reused_scans += 1
        else:
            assessment = assess_report(report)
            boe_path = write_boe(
                root=generated_dir,
                skill=skill,
                scan_key=scan_key,
                report=report,
                assessment=assessment,
                validation=validation,
                report_path=report_source,
            )
        zip_path = write_skill_zip(skill, generated_dir / "zips")
        detail_path = generated_dir / "skills" / f"{skill.metadata.namespace}--{skill.metadata.skill_id}.json"
        detail_path.parent.mkdir(parents=True, exist_ok=True)

        record = {
            "namespace": skill.metadata.namespace,
            "skill_id": skill.metadata.skill_id,
            "display_id": skill.metadata.display_id,
            "name": skill.metadata.name,
            "description": skill.metadata.description,
            "category": skill.metadata.category,
            "tags": list(skill.metadata.tags),
            "owner": skill.metadata.owner,
            "owner_missing": "missing_owner" in validation.metadata_flags,
            "upstream_url": skill.metadata.upstream_url,
            "content_hash": skill.content_hash,
            "risk": assessment["risk"],
            "risk_reason": assessment["reason"],
            "confidence_flags": assessment["confidence_flags"],
            "scan_mode": report.get("mode", "unknown"),
            "boe_path": boe_path.as_posix(),
            "detail_path": detail_path.as_posix(),
            "zip_path": zip_path.as_posix(),
            "download_path": f"/downloads/{zip_path.name}",
            "warnings": list(validation.warnings),
            "metadata_flags": list(validation.metadata_flags),
        }
        detail_path.write_text(json.dumps(record, indent=2, sort_keys=True) + "\n")

        if record["risk"] != "Unknown" or policy.show_unknown_risk:
            records.append(record)

    index = {"schema_version": "skill-exchange-index/v0", "skills": records}
    (generated_dir / "index.json").write_text(json.dumps(index, indent=2, sort_keys=True) + "\n")
    return {"skills_written": len(records), "reused_scans": reused_scans}


def make_scan_key(content_hash: str, report: dict[str, Any]) -> str:
    scanner = report.get("scanner", {})
    name = scanner.get("name", "skillspector")
    version = scanner.get("version", "unknown")
    mode = report.get("mode", "unknown")
    return f"{content_hash}--{name}-{version}--{mode}"


def boe_path_for(generated_dir: Path, skill, scan_key: str) -> Path:
    return (
        generated_dir
        / "boe"
        / skill.metadata.namespace
        / skill.metadata.skill_id
        / skill.content_hash
        / scan_key
        / "boe.json"
    )


def assessment_from_boe(boe_path: Path) -> dict[str, Any]:
    boe = json.loads(boe_path.read_text())
    return {
        "risk": boe["risk"],
        "reason": boe["risk_reason"],
        "confidence_flags": boe.get("confidence_flags", []),
    }
