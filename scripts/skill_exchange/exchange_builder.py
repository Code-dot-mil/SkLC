from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .boe import write_boe
from .policy import load_exchange_policy
from .risk import assess_report
from .skills import discover_skills
from .skillspector import run_skillspector
from .validation import validate_skill
from .zipper import write_skill_zip


def build_exchange(
    *,
    skills_root: Path,
    exchange_dir: Path,
    generated_dir: Path,
    scan_modes: tuple[str, ...],
) -> dict[str, Any]:
    generated_dir.mkdir(parents=True, exist_ok=True)
    policy = load_exchange_policy(exchange_dir)
    skills = discover_skills(skills_root)
    records: list[dict[str, Any]] = []
    skill_rows: list[dict[str, Any]] = []
    scanner_run_rows: list[dict[str, Any]] = []
    scanner_artifact_rows: list[dict[str, Any]] = []
    scanner_finding_rows: list[dict[str, Any]] = []
    reused_scans = 0

    for skill in skills:
        validation = validate_skill(skill, policy)
        skill_scanner_runs: list[dict[str, Any]] = []
        for mode in scan_modes:
            no_llm = mode == "static-only"
            report_source = generated_dir / "tmp" / skill.metadata.namespace / skill.metadata.skill_id / mode / "report.json"
            report = run_skillspector(skill.path, report_source, no_llm=no_llm)

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
            native_report_path = boe_path.parent / "skillspector.json"
            summary_path = boe_path.parent / "summary.json"
            scanner_run = scanner_run_row(
                skill=skill,
                report=report,
                assessment=assessment,
                scan_key=scan_key,
                boe_path=boe_path,
                native_report_path=native_report_path,
                summary_path=summary_path,
            )
            skill_scanner_runs.append(scanner_run)
            scanner_run_rows.append(scanner_run)
            scanner_artifact_rows.extend(scanner_artifact_rows_for(scanner_run))
            scanner_finding_rows.extend(scanner_finding_rows_for(scanner_run["id"], report))
        zip_path = write_skill_zip(skill, generated_dir / "zips")
        detail_path = generated_dir / "skills" / f"{skill.metadata.namespace}--{skill.metadata.skill_id}.json"
        detail_path.parent.mkdir(parents=True, exist_ok=True)
        aggregate = aggregate_assessment(skill_scanner_runs)

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
            "risk": aggregate["risk"],
            "risk_reason": aggregate["reason"],
            "confidence_flags": aggregate["confidence_flags"],
            "scan_modes": [row["scan_mode"] for row in skill_scanner_runs],
            "scanner_run_ids": [row["id"] for row in skill_scanner_runs],
            "boe_path": skill_scanner_runs[-1]["boe_path"],
            "detail_path": detail_path.as_posix(),
            "zip_path": zip_path.as_posix(),
            "download_path": f"/downloads/{zip_path.name}",
            "warnings": list(validation.warnings),
            "metadata_flags": list(validation.metadata_flags),
        }
        detail_path.write_text(json.dumps(record, indent=2, sort_keys=True) + "\n")
        skill_rows.append(record)

        if record["risk"] != "Unknown" or policy.show_unknown_risk:
            records.append(record)

    write_table(generated_dir, "skills", skill_rows)
    write_table(generated_dir, "scanner_runs", scanner_run_rows)
    write_table(generated_dir, "scanner_artifacts", scanner_artifact_rows)
    write_table(generated_dir, "scanner_findings", scanner_finding_rows)
    index = {"schema_version": "skill-exchange-index/v0", "skills": records}
    (generated_dir / "index.json").write_text(json.dumps(index, indent=2, sort_keys=True) + "\n")
    return {"skills_written": len(records), "reused_scans": reused_scans}


def make_scan_key(content_hash: str, report: dict[str, Any]) -> str:
    metadata = report.get("metadata", {})
    name = "skillspector"
    version = metadata.get("skillspector_version", "unknown") if isinstance(metadata, dict) else "unknown"
    mode = scan_mode(report)
    return f"{content_hash}--{name}-{version}--{mode}"


def scan_mode(report: dict[str, Any]) -> str:
    metadata = report.get("metadata", {})
    if isinstance(metadata, dict) and metadata.get("llm_requested") is False:
        return "static-only"
    return "llm-assisted"


def scanner_run_row(
    *,
    skill,
    report: dict[str, Any],
    assessment: dict[str, Any],
    scan_key: str,
    boe_path: Path,
    native_report_path: Path,
    summary_path: Path,
) -> dict[str, Any]:
    metadata = report.get("metadata") if isinstance(report.get("metadata"), dict) else {}
    risk_assessment = report.get("risk_assessment") if isinstance(report.get("risk_assessment"), dict) else {}
    return {
        "id": scan_key,
        "skill_display_id": skill.metadata.display_id,
        "namespace": skill.metadata.namespace,
        "skill_id": skill.metadata.skill_id,
        "content_hash": skill.content_hash,
        "scanner_name": "skillspector",
        "scanner_type": "security",
        "scanner_version": metadata.get("skillspector_version", "unknown"),
        "scan_mode": scan_mode(report),
        "native_output_format": "skillspector-json-v2",
        "native_report_path": native_report_path.as_posix(),
        "summary_path": summary_path.as_posix(),
        "boe_path": boe_path.as_posix(),
        "status": "completed",
        "native_score": risk_assessment.get("score"),
        "native_severity": risk_assessment.get("severity"),
        "native_recommendation": risk_assessment.get("recommendation"),
        "display_risk": assessment["risk"],
        "display_risk_reason": assessment["reason"],
        "confidence_flags": assessment["confidence_flags"],
    }


def scanner_artifact_rows_for(scanner_run: dict[str, Any]) -> list[dict[str, Any]]:
    run_id = scanner_run["id"]
    return [
        {
            "id": f"{run_id}:native_report",
            "scanner_run_id": run_id,
            "artifact_kind": "native_report",
            "path": scanner_run["native_report_path"],
            "media_type": "application/vnd.skillspector.report+json",
        },
        {
            "id": f"{run_id}:summary",
            "scanner_run_id": run_id,
            "artifact_kind": "summary",
            "path": scanner_run["summary_path"],
            "media_type": "application/json",
        },
        {
            "id": f"{run_id}:boe",
            "scanner_run_id": run_id,
            "artifact_kind": "boe",
            "path": scanner_run["boe_path"],
            "media_type": "application/json",
        },
    ]


def scanner_finding_rows_for(scanner_run_id: str, report: dict[str, Any]) -> list[dict[str, Any]]:
    issues = report.get("issues")
    if not isinstance(issues, list):
        return []
    rows = []
    for index, issue in enumerate(issues):
        if not isinstance(issue, dict):
            continue
        location = issue.get("location") if isinstance(issue.get("location"), dict) else {}
        issue_id = str(issue.get("id") or f"issue-{index + 1}")
        rows.append(
            {
                "id": f"{scanner_run_id}:{issue_id}:{index}",
                "scanner_run_id": scanner_run_id,
                "native_issue_id": issue_id,
                "severity": issue.get("severity"),
                "category": issue.get("category"),
                "path": location.get("file"),
                "start_line": location.get("start_line"),
                "end_line": location.get("end_line"),
                "native_finding_json": issue,
            }
        )
    return rows


def write_table(generated_dir: Path, name: str, rows: list[dict[str, Any]]) -> None:
    path = generated_dir / "tables" / f"{name}.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "schema_version": f"skill-exchange-table/{name}/v0",
        "rows": rows,
    }
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")


def aggregate_assessment(scanner_runs: list[dict[str, Any]]) -> dict[str, Any]:
    rank = {"Unknown": 0, "Low": 1, "Medium": 2, "High": 3}
    selected = max(scanner_runs, key=lambda row: rank.get(row["display_risk"], 0))
    flags = []
    for row in scanner_runs:
        for flag in row["confidence_flags"]:
            if flag not in flags:
                flags.append(flag)
    return {
        "risk": selected["display_risk"],
        "reason": selected["display_risk_reason"],
        "confidence_flags": flags,
    }


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
