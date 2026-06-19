from __future__ import annotations

import json
import os
import shutil
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .boe import write_boe
from .policy import load_exchange_policy
from .risk import assess_report
from .skills import discover_skills
from .skillspector import run_skillspector, skillspector_llm_config
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
    site_config = load_site_config(exchange_dir)
    skills = discover_skills(skills_root)
    records: list[dict[str, Any]] = []
    skill_rows: list[dict[str, Any]] = []
    scanner_run_rows: list[dict[str, Any]] = [
        row for row in existing_table_rows(generated_dir, "scanner_runs") if row.get("scan_cache_key")
    ]
    historical_run_ids = {row["id"] for row in scanner_run_rows}
    scanner_artifact_rows: list[dict[str, Any]] = [
        row for row in existing_table_rows(generated_dir, "scanner_artifacts") if row.get("scanner_run_id") in historical_run_ids
    ]
    scanner_finding_rows: list[dict[str, Any]] = [
        row for row in existing_table_rows(generated_dir, "scanner_findings") if row.get("scanner_run_id") in historical_run_ids
    ]
    reused_scans = 0

    for skill in skills:
        validation = validate_skill(skill, policy)
        skill_scanner_runs: list[dict[str, Any]] = []
        last_updated = skill_last_updated(skill)
        first_observed = skill_first_observed(skill)
        for mode in scan_modes:
            no_llm = mode == "static-only"
            report_source = generated_dir / "tmp" / skill.metadata.namespace / skill.metadata.skill_id / mode / "report.json"
            report = run_skillspector(skill.path, report_source, no_llm=no_llm)
            last_scanned = datetime.now(timezone.utc).isoformat()

            scan_key = make_scan_key(skill.content_hash, report)
            run_id = make_run_id(scan_key, last_scanned)
            existing_boe_path = boe_path_for(generated_dir, skill, scan_key)
            assessment = assess_report(report)
            if existing_boe_path.exists():
                reused_scans += 1
            boe_path = write_boe(
                root=generated_dir,
                skill=skill,
                scan_key=scan_key,
                report=report,
                assessment=assessment,
                validation=validation,
                report_path=report_source,
            )
            run_artifacts = write_run_artifacts(
                generated_dir=generated_dir,
                run_id=run_id,
                report_path=report_source,
                boe_path=boe_path,
                assessment=assessment,
            )
            scanner_run = scanner_run_row(
                skill=skill,
                report=report,
                assessment=assessment,
                run_id=run_id,
                scan_key=scan_key,
                boe_path=run_artifacts["boe_path"],
                native_report_path=run_artifacts["native_report_path"],
                summary_path=run_artifacts["summary_path"],
                last_scanned=last_scanned,
            )
            skill_scanner_runs.append(scanner_run)
            scanner_run_rows.append(scanner_run)
            scanner_artifact_rows.extend(scanner_artifact_rows_for(scanner_run))
            scanner_finding_rows.extend(scanner_finding_rows_for(scanner_run["id"], report))
        zip_path = write_skill_zip(skill, generated_dir / "zips")
        detail_path = generated_dir / "skills" / f"{skill.metadata.namespace}--{skill.metadata.skill_id}.json"
        detail_path.parent.mkdir(parents=True, exist_ok=True)
        aggregate = aggregate_assessment(skill_scanner_runs)
        last_scanned = max(row["last_scanned"] for row in skill_scanner_runs)

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
            "skill_files": skill_files(skill),
            "skill_md_content": skill.skill_file.read_text(),
            "source_path": skill.path.as_posix(),
            "source_url": source_url(site_config, skill.path.as_posix()),
            "last_updated": last_updated,
            "first_observed": first_observed,
            "last_scanned": last_scanned,
            "recommendation": aggregate["recommendation"],
            "confidence_flags": aggregate["confidence_flags"],
            "scan_mode": aggregate["scan_mode"],
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

        if aggregate["risk"] != "Unknown" or policy.show_unknown_risk:
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


def make_run_id(scan_key: str, last_scanned: str) -> str:
    timestamp = last_scanned.replace("-", "").replace(":", "").replace("+", "").replace(".", "")
    return f"{scan_key}--{timestamp}"


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
    run_id: str,
    scan_key: str,
    boe_path: Path,
    native_report_path: Path,
    summary_path: Path,
    last_scanned: str,
) -> dict[str, Any]:
    metadata = report.get("metadata") if isinstance(report.get("metadata"), dict) else {}
    risk_assessment = report.get("risk_assessment") if isinstance(report.get("risk_assessment"), dict) else {}
    mode = scan_mode(report)
    llm_config = skillspector_llm_config() if mode == "llm-assisted" else {"provider": None, "model": None}
    return {
        "id": run_id,
        "scan_cache_key": scan_key,
        "skill_display_id": skill.metadata.display_id,
        "namespace": skill.metadata.namespace,
        "skill_id": skill.metadata.skill_id,
        "content_hash": skill.content_hash,
        "last_scanned": last_scanned,
        "scanner_name": "skillspector",
        "scanner_type": "security",
        "scanner_version": metadata.get("skillspector_version", "unknown"),
        "scan_mode": mode,
        "llm_provider": llm_config["provider"],
        "llm_model": llm_config["model"],
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
            "download_path": f"/downloads/scanner-runs/{run_id}/skillspector.json",
            "media_type": "application/vnd.skillspector.report+json",
        },
        {
            "id": f"{run_id}:summary",
            "scanner_run_id": run_id,
            "artifact_kind": "summary",
            "path": scanner_run["summary_path"],
            "download_path": f"/downloads/scanner-runs/{run_id}/summary.json",
            "media_type": "application/json",
        },
        {
            "id": f"{run_id}:boe",
            "scanner_run_id": run_id,
            "artifact_kind": "boe",
            "path": scanner_run["boe_path"],
            "download_path": f"/downloads/scanner-runs/{run_id}/boe.json",
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
                "pattern": issue.get("pattern"),
                "confidence": issue.get("confidence"),
                "path": location.get("file"),
                "start_line": location.get("start_line"),
                "end_line": location.get("end_line"),
                "explanation": issue.get("explanation"),
                "remediation": issue.get("remediation"),
                "code_snippet": issue.get("code_snippet"),
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


def existing_table_rows(generated_dir: Path, name: str) -> list[dict[str, Any]]:
    path = generated_dir / "tables" / f"{name}.json"
    if not path.exists():
        return []
    payload = json.loads(path.read_text())
    rows = payload.get("rows")
    return rows if isinstance(rows, list) else []


def write_run_artifacts(
    *,
    generated_dir: Path,
    run_id: str,
    report_path: Path,
    boe_path: Path,
    assessment: dict[str, Any],
) -> dict[str, Path]:
    run_dir = generated_dir / "scanner-runs" / run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    native_report_path = run_dir / "skillspector.json"
    summary_path = run_dir / "summary.json"
    run_boe_path = run_dir / "boe.json"
    shutil.copyfile(report_path, native_report_path)
    shutil.copyfile(boe_path, run_boe_path)
    summary_path.write_text(json.dumps(assessment, indent=2, sort_keys=True) + "\n")
    return {
        "native_report_path": native_report_path,
        "summary_path": summary_path,
        "boe_path": run_boe_path,
    }


def aggregate_assessment(scanner_runs: list[dict[str, Any]]) -> dict[str, Any]:
    mode_rank = {"static-only": 0, "llm-assisted": 1}
    selected = max(
        scanner_runs,
        key=lambda row: (
            row.get("last_scanned") or "",
            mode_rank.get(row.get("scan_mode"), 0),
        ),
    )
    return {
        "risk": selected["display_risk"],
        "reason": selected["display_risk_reason"],
        "recommendation": selected["native_recommendation"] or "Unknown",
        "scan_mode": selected["scan_mode"],
        "confidence_flags": selected["confidence_flags"],
    }


def skill_files(skill) -> list[dict[str, Any]]:
    rows = []
    for path in sorted(item for item in skill.path.rglob("*") if item.is_file()):
        rows.append(
            {
                "path": path.relative_to(skill.path).as_posix(),
                "size_bytes": path.stat().st_size,
            }
        )
    return rows


def load_site_config(exchange_dir: Path) -> dict[str, Any]:
    path = exchange_dir / "site-config.json"
    config = json.loads(path.read_text()) if path.exists() else {}
    source_repository_url = os.environ.get("SKILL_EXCHANGE_SOURCE_REPOSITORY_URL")
    source_branch = os.environ.get("SKILL_EXCHANGE_SOURCE_BRANCH")
    if source_repository_url:
        config["sourceRepositoryUrl"] = source_repository_url
    if source_branch:
        config["sourceBranch"] = source_branch
    return config


def source_url(site_config: dict[str, Any], source_path: str) -> str | None:
    repository_url = str(site_config.get("sourceRepositoryUrl") or "").rstrip("/")
    branch = str(site_config.get("sourceBranch") or "main").strip("/")
    if not repository_url:
        return None
    return f"{repository_url}/tree/{branch}/{source_path}"


def skill_last_updated(skill) -> str:
    completed = subprocess.run(
        ["git", "log", "-1", "--format=%cI", "--", skill.path.as_posix()],
        text=True,
        capture_output=True,
        check=False,
    )
    timestamp = completed.stdout.strip()
    if timestamp:
        return timestamp

    newest_mtime = max(path.stat().st_mtime for path in skill.path.rglob("*") if path.is_file())
    return datetime.fromtimestamp(newest_mtime, tz=timezone.utc).isoformat()


def skill_first_observed(skill) -> str:
    completed = subprocess.run(
        ["git", "log", "--reverse", "--format=%cI", "--", skill.path.as_posix()],
        text=True,
        capture_output=True,
        check=False,
    )
    timestamp = completed.stdout.splitlines()[0].strip() if completed.stdout.splitlines() else ""
    if timestamp:
        return timestamp

    oldest_mtime = min(path.stat().st_mtime for path in skill.path.rglob("*") if path.is_file())
    return datetime.fromtimestamp(oldest_mtime, tz=timezone.utc).isoformat()


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
