from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
from datetime import UTC, datetime
from hashlib import sha256
from pathlib import Path
from typing import Any

from .boe import write_boe
from .policy import load_exchange_policy
from .risk import assess_report
from .skills import discover_skills
from .skillspector import run_skillspector, skillspector_llm_config, skillspector_version
from .validation import validate_skill
from .zipper import write_skill_zip

TRACKED_BOE_FILES = {
    "boe.json",
    "hashes.json",
    "scanner-config.json",
    "skillspector.json",
    "summary.json",
}
TRACKED_BOE_HASHED_FILES = TRACKED_BOE_FILES - {"hashes.json"}
RECOMMENDATION_LABELS = {
    "SAFE": "Safe to use",
    "CAUTION": "Use caution",
    "DO_NOT_INSTALL": "Avoid installing",
    "BLOCK": "Avoid installing",
    "Unknown": "Unknown",
}


def build_exchange(
    *,
    skills_root: Path,
    exchange_dir: Path,
    generated_dir: Path,
    scan_modes: tuple[str, ...],
    reuse_boe_only: bool = False,
) -> dict[str, Any]:
    generated_dir.mkdir(parents=True, exist_ok=True)
    zip_dir = generated_dir / "zips"
    if zip_dir.exists():
        shutil.rmtree(zip_dir)
    policy = load_exchange_policy(exchange_dir)
    site_config = load_site_config(exchange_dir)
    skills = discover_skills(skills_root)
    records: list[dict[str, Any]] = []
    skill_rows: list[dict[str, Any]] = []
    scanner_run_rows: list[dict[str, Any]] = []
    if not reuse_boe_only:
        scanner_run_rows = [
            row for row in existing_table_rows(generated_dir, "scanner_runs") if row.get("scan_cache_key")
        ]
    historical_run_ids = {row["id"] for row in scanner_run_rows}
    scanner_artifact_rows: list[dict[str, Any]] = [
        row
        for row in existing_table_rows(generated_dir, "scanner_artifacts")
        if row.get("scanner_run_id") in historical_run_ids
    ]
    scanner_finding_rows: list[dict[str, Any]] = [
        row
        for row in existing_table_rows(generated_dir, "scanner_findings")
        if row.get("scanner_run_id") in historical_run_ids
    ]
    cached_scanner_runs = latest_scanner_runs_by_cache_key(scanner_run_rows)
    reused_scans = 0
    invalid_skills: list[str] = []
    valid_skills = []
    reusable_boes: dict[tuple[str, str], dict[str, Any]] = {}
    missing_boes: list[str] = []

    for skill in skills:
        validation = validate_skill(skill, policy)
        if validation.errors:
            invalid_skills.append(skill.metadata.display_id)
            continue
        valid_skills.append((skill, validation))

    if reuse_boe_only:
        for skill, _validation in valid_skills:
            for mode in scan_modes:
                cached_boe = read_latest_tracked_boe(generated_dir=generated_dir, skill=skill, mode=mode)
                if cached_boe is None:
                    missing_boes.append(f"{skill.metadata.display_id} ({mode})")
                    continue
                reusable_boes[(skill.metadata.display_id, mode)] = cached_boe
        if missing_boes:
            raise RuntimeError("missing tracked BOE for exact skill content: " + ", ".join(missing_boes))

    for skill, validation in valid_skills:
        skill_scanner_runs: list[dict[str, Any]] = []
        last_updated = skill_last_updated(skill)
        first_observed = skill_first_observed(skill)
        latest_source_commit_sha = skill_latest_source_commit_sha(skill)
        for mode in scan_modes:
            if reuse_boe_only:
                cached_boe = reusable_boes[(skill.metadata.display_id, mode)]
                scanner_version = cached_boe["scanner_version"]
                scanner_config = cached_boe["scanner_config"]
                scan_key = cached_boe["scan_key"]
            else:
                scanner_version = skillspector_version()
                scanner_config = scanner_cache_config(mode)
                scan_key = make_scan_key(
                    namespace=skill.metadata.namespace,
                    skill_id=skill.metadata.skill_id,
                    content_hash=skill.content_hash,
                    scanner_version=scanner_version,
                    mode=mode,
                    scanner_config=scanner_config,
                )
                cached_scanner_run = cached_scanner_runs.get(scan_key)
                cached_report = read_cached_report(cached_scanner_run) if cached_scanner_run else None
                if cached_scanner_run and cached_report:
                    reused_scans += 1
                    skill_scanner_runs.append(cached_scanner_run)
                    continue
                cached_boe = read_cached_boe(generated_dir=generated_dir, skill=skill, scan_key=scan_key)
            if cached_boe:
                report = cached_boe["report"]
                assessment = assess_report(report)
                last_scanned = cached_boe["scan_timestamp"]
                run_id = make_run_id(scan_key, last_scanned)
                run_artifacts = write_run_artifacts(
                    generated_dir=generated_dir,
                    run_id=run_id,
                    report_path=cached_boe["report_path"],
                    boe_path=cached_boe["boe_path"],
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
                    scanner_version=scanner_version,
                    scanner_config=scanner_config,
                    status="completed",
                    canonical_boe_path=cached_boe["boe_path"],
                )
                reused_scans += 1
                skill_scanner_runs.append(scanner_run)
                scanner_run_rows.append(scanner_run)
                cached_scanner_runs[scan_key] = scanner_run
                scanner_artifact_rows.extend(scanner_artifact_rows_for(scanner_run))
                scanner_finding_rows.extend(scanner_finding_rows_for(scanner_run["id"], report))
                continue

            no_llm = mode == "static-only"
            report_source = (
                generated_dir
                / "tmp"
                / skill.metadata.namespace
                / skill.metadata.skill_id
                / mode
                / "report.json"
            )
            scan_status = "completed"
            try:
                report = run_skillspector(skill.path, report_source, no_llm=no_llm)
            except Exception as exc:
                scan_status = "failed"
                report = scanner_failure_report(mode=mode, scanner_version=scanner_version, error=exc)
                report_source.parent.mkdir(parents=True, exist_ok=True)
                report_source.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
            last_scanned = datetime.now(UTC).isoformat()

            run_id = make_run_id(scan_key, last_scanned)
            assessment = assess_report(report)
            boe_path = write_boe(
                root=generated_dir,
                skill=skill,
                scan_key=scan_key,
                report=report,
                assessment=assessment,
                validation=validation,
                report_path=report_source,
                source_commit_sha=latest_source_commit_sha,
                scan_timestamp=last_scanned,
                scanner_config=scanner_config,
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
                scanner_version=scanner_version,
                scanner_config=scanner_config,
                status=scan_status,
                canonical_boe_path=boe_path,
            )
            skill_scanner_runs.append(scanner_run)
            scanner_run_rows.append(scanner_run)
            cached_scanner_runs[scan_key] = scanner_run
            scanner_artifact_rows.extend(scanner_artifact_rows_for(scanner_run))
            scanner_finding_rows.extend(scanner_finding_rows_for(scanner_run["id"], report))
        zip_path = write_skill_zip(skill, zip_dir)
        detail_path = generated_dir / "skills" / f"{skill.metadata.namespace}--{skill.metadata.skill_id}.json"
        detail_path.parent.mkdir(parents=True, exist_ok=True)
        aggregate = aggregate_assessment(skill_scanner_runs)
        selected_run = select_scanner_run(skill_scanner_runs)
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
            "latest_source_commit_sha": latest_source_commit_sha,
            "last_scanned": last_scanned,
            "risk": aggregate["risk"],
            "risk_reason": aggregate["reason"],
            "recommendation": aggregate["recommendation"],
            "recommendation_label": aggregate["recommendation_label"],
            "confidence_flags": aggregate["confidence_flags"],
            "scan_mode": aggregate["scan_mode"],
            "scan_modes": [row["scan_mode"] for row in skill_scanner_runs],
            "scanner_provenance": scanner_provenance(selected_run),
            "scanner_run_ids": [row["id"] for row in skill_scanner_runs],
            "boe_path": selected_run.get("canonical_boe_path") or selected_run["boe_path"],
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
    return {"skills_written": len(records), "reused_scans": reused_scans, "invalid_skills": invalid_skills}


def scanner_failure_report(*, mode: str, scanner_version: str, error: Exception) -> dict[str, Any]:
    return {
        "metadata": {
            "llm_requested": mode != "static-only",
            "skillspector_version": scanner_version,
            "scan_error": str(error),
        },
        "scanner_error": str(error),
    }


def make_scan_key(
    *,
    namespace: str,
    skill_id: str,
    content_hash: str,
    scanner_version: str,
    mode: str,
    scanner_config: dict[str, Any],
) -> str:
    config_label = scanner_config_label(scanner_config)
    config_hash = scanner_config_hash(scanner_config)
    return (
        f"{namespace}--{skill_id}--{content_hash}--skillspector-{scanner_version}"
        f"--{mode}--{config_label}--{config_hash}"
    )


def scanner_config_label(scanner_config: dict[str, Any]) -> str:
    if scanner_config.get("scan_mode") != "llm-assisted":
        return "no-llm"
    provider = safe_key_part(scanner_config.get("llm_provider") or "unknown-provider")
    model = safe_key_part(scanner_config.get("llm_model") or "unknown-model")
    return f"{provider}-{model}"


def safe_key_part(value: Any) -> str:
    return re.sub(r"[^A-Za-z0-9_.-]+", "-", str(value)).strip("-") or "unknown"


def scanner_config_hash(scanner_config: dict[str, Any]) -> str:
    encoded = json.dumps(scanner_config, sort_keys=True, separators=(",", ":"))
    return sha256(encoded.encode()).hexdigest()[:16]


def scanner_cache_config(mode: str) -> dict[str, Any]:
    config: dict[str, Any] = {
        "native_output_format": "skillspector-json-v2",
        "scan_mode": mode,
    }
    if mode == "llm-assisted":
        llm_config = skillspector_llm_config()
        config["llm_provider"] = llm_config["provider"]
        config["llm_model"] = llm_config["model"]
    return config


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
    scanner_version: str,
    scanner_config: dict[str, Any],
    status: str = "completed",
    canonical_boe_path: Path | None = None,
) -> dict[str, Any]:
    metadata = report.get("metadata") if isinstance(report.get("metadata"), dict) else {}
    risk_assessment = report.get("risk_assessment") if isinstance(report.get("risk_assessment"), dict) else {}
    mode = scan_mode(report)
    llm_config = (
        {
            "provider": scanner_config.get("llm_provider"),
            "model": scanner_config.get("llm_model"),
        }
        if mode == "llm-assisted"
        else {"provider": None, "model": None}
    )
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
        "scanner_version": metadata.get("skillspector_version") or scanner_version,
        "scanner_config_hash": scanner_config_hash(scanner_config),
        "scan_mode": mode,
        "llm_provider": llm_config["provider"],
        "llm_model": llm_config["model"],
        "native_output_format": "skillspector-json-v2",
        "native_report_path": native_report_path.as_posix(),
        "summary_path": summary_path.as_posix(),
        "boe_path": boe_path.as_posix(),
        "canonical_boe_path": (canonical_boe_path or boe_path).as_posix(),
        "status": status,
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


def latest_scanner_runs_by_cache_key(scanner_runs: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    cached: dict[str, dict[str, Any]] = {}
    for row in scanner_runs:
        cache_key = row.get("scan_cache_key")
        if not cache_key:
            continue
        existing = cached.get(cache_key)
        if not existing or str(row.get("last_scanned") or "") > str(existing.get("last_scanned") or ""):
            cached[cache_key] = row
    return cached


def read_cached_report(scanner_run: dict[str, Any] | None) -> dict[str, Any] | None:
    if not scanner_run:
        return None
    path_value = scanner_run.get("native_report_path")
    if not path_value:
        return None
    path = Path(path_value)
    if not path.exists():
        return None
    report = json.loads(path.read_text())
    return report if isinstance(report, dict) else None


def read_cached_boe(*, generated_dir: Path, skill, scan_key: str) -> dict[str, Any] | None:
    for candidate_key in equivalent_scan_keys(scan_key):
        boe_path = boe_path_for(generated_dir, skill, candidate_key)
        if boe_path.exists():
            return read_boe_bundle(boe_path=boe_path, scan_key=candidate_key)
    return None


def read_latest_tracked_boe(*, generated_dir: Path, skill, mode: str) -> dict[str, Any] | None:
    skill_boe_root = (
        generated_dir
        / "boe"
        / skill.metadata.namespace
        / skill.metadata.skill_id
        / skill.content_hash
    )
    candidates: list[tuple[datetime, str, dict[str, Any]]] = []
    for boe_path in sorted(skill_boe_root.glob("*/boe.json")):
        try:
            bundle = read_verified_tracked_boe_bundle(
                generated_dir=generated_dir,
                boe_path=boe_path,
                skill=skill,
                mode=mode,
            )
            if bundle is None:
                continue
            scan_key = bundle["scan_key"]
            scan_timestamp = datetime.fromisoformat(bundle["scan_timestamp"])
            if scan_timestamp.tzinfo is None:
                continue
        except (OSError, ValueError, json.JSONDecodeError):
            continue
        candidates.append((scan_timestamp.astimezone(UTC), scan_key, bundle))
    if not candidates:
        return None
    return max(candidates, key=lambda candidate: (candidate[0], candidate[1]))[2]


def read_verified_tracked_boe_bundle(
    *, generated_dir: Path, boe_path: Path, skill, mode: str
) -> dict[str, Any] | None:
    bundle_dir = boe_path.parent
    required_paths = {filename: bundle_dir / filename for filename in TRACKED_BOE_FILES}
    if any(
        not path.is_file() or path_has_symlink_within(path=path, scope=generated_dir)
        for path in required_paths.values()
    ):
        return None

    hashes = json.loads(required_paths["hashes.json"].read_text())
    if not isinstance(hashes, dict) or set(hashes) != TRACKED_BOE_HASHED_FILES:
        return None
    for filename in TRACKED_BOE_HASHED_FILES:
        expected_hash = hashes.get(filename)
        if (
            not isinstance(expected_hash, str)
            or re.fullmatch(r"[0-9a-f]{64}", expected_hash) is None
            or sha256(required_paths[filename].read_bytes()).hexdigest() != expected_hash
        ):
            return None

    boe = json.loads(required_paths["boe.json"].read_text())
    scanner_config = json.loads(required_paths["scanner-config.json"].read_text())
    report = json.loads(required_paths["skillspector.json"].read_text())
    summary = json.loads(required_paths["summary.json"].read_text())
    if not all(isinstance(value, dict) for value in (boe, scanner_config, report, summary)):
        return None
    if boe.get("schema_version") != "skill-exchange-boe/v0":
        return None

    scan_key = str(boe.get("scan_cache_key") or "")
    scanner = boe.get("scanner") if isinstance(boe.get("scanner"), dict) else {}
    scanner_version = str(scanner.get("version") or "")
    if (
        boe.get("namespace") != skill.metadata.namespace
        or boe.get("skill_id") != skill.metadata.skill_id
        or boe.get("display_id") != skill.metadata.display_id
        or boe.get("skill_content_hash") != skill.content_hash
        or boe.get("scan_mode") != mode
        or scanner.get("name") != "skillspector"
        or not scan_key
        or not scanner_version
        or bundle_dir.name != scan_key
        or scanner_config.get("scan_mode") != mode
    ):
        return None

    expected_scan_key = make_scan_key(
        namespace=skill.metadata.namespace,
        skill_id=skill.metadata.skill_id,
        content_hash=skill.content_hash,
        scanner_version=scanner_version,
        mode=mode,
        scanner_config=scanner_config,
    )
    if scan_key not in equivalent_scan_keys(expected_scan_key):
        return None

    report_metadata = report.get("metadata") if isinstance(report.get("metadata"), dict) else {}
    expected_llm_requested = mode == "llm-assisted"
    if (
        str(report_metadata.get("skillspector_version") or "") != scanner_version
        or report_metadata.get("llm_requested") is not expected_llm_requested
        or boe.get("provider") != scanner_config.get("llm_provider")
        or boe.get("model") != scanner_config.get("llm_model")
    ):
        return None
    if mode == "static-only" and (
        scanner_config.get("llm_provider") is not None or scanner_config.get("llm_model") is not None
    ):
        return None
    if mode == "llm-assisted" and (
        not scanner_config.get("llm_provider") or not scanner_config.get("llm_model")
    ):
        return None

    if not is_successful_skillspector_report(report):
        return None
    assessment = assess_report(report)
    expected_summary = {
        "risk": assessment["risk"],
        "risk_reason": assessment["reason"],
        "confidence_flags": assessment["confidence_flags"],
    }
    if (
        assessment["risk"] == "Unknown"
        or summary != expected_summary
        or boe.get("risk") != assessment["risk"]
        or boe.get("risk_reason") != assessment["reason"]
        or boe.get("confidence_flags") != assessment["confidence_flags"]
    ):
        return None

    scan_timestamp = boe.get("scan_timestamp") or boe.get("generated_at")
    if not scan_timestamp:
        return None
    return {
        "boe": boe,
        "boe_path": boe_path,
        "report": report,
        "report_path": required_paths["skillspector.json"],
        "scan_timestamp": str(scan_timestamp),
        "scan_key": scan_key,
        "scanner_config": scanner_config,
        "scanner_version": scanner_version,
    }


def is_successful_skillspector_report(report: dict[str, Any]) -> bool:
    metadata = report.get("metadata") if isinstance(report.get("metadata"), dict) else {}
    issues = report.get("issues")
    risk_assessment = report.get("risk_assessment")
    if (
        report.get("scanner_error")
        or metadata.get("scan_error")
        or not isinstance(issues, list)
        or not all(isinstance(issue, dict) for issue in issues)
        or not isinstance(risk_assessment, dict)
    ):
        return False
    score = risk_assessment.get("score")
    severity = str(risk_assessment.get("severity") or "").lower()
    recommendation = risk_assessment.get("recommendation")
    return (
        isinstance(score, (int, float))
        and not isinstance(score, bool)
        and 0 <= score <= 100
        and severity in {"low", "medium", "high", "critical"}
        and isinstance(recommendation, str)
        and bool(recommendation.strip())
    )


def path_has_symlink_within(*, path: Path, scope: Path) -> bool:
    try:
        relative_path = path.relative_to(scope)
    except ValueError:
        return True
    candidate = scope
    if candidate.is_symlink():
        return True
    for part in relative_path.parts:
        candidate /= part
        if candidate.is_symlink():
            return True
    return False


def equivalent_scan_keys(scan_key: str) -> list[str]:
    keys = [scan_key]
    prefix, marker, suffix = scan_key.partition("--skillspector-")
    if not marker:
        return keys
    scanner_version, separator, tail = suffix.partition("--")
    if not separator:
        return keys
    if len(scanner_version) > 1 and scanner_version.startswith("v") and scanner_version[1].isdigit():
        alternate_version = scanner_version[1:]
    else:
        alternate_version = f"v{scanner_version}"
    alternate_key = f"{prefix}{marker}{alternate_version}{separator}{tail}"
    if alternate_key not in keys:
        keys.append(alternate_key)
    return keys


def read_boe_bundle(*, boe_path: Path, scan_key: str) -> dict[str, Any] | None:
    boe = json.loads(boe_path.read_text())
    if not isinstance(boe, dict):
        return None
    if boe.get("schema_version") != "skill-exchange-boe/v0":
        return None
    if boe.get("scan_cache_key") != scan_key:
        return None
    scan_timestamp = boe.get("scan_timestamp") or boe.get("generated_at")
    if not scan_timestamp:
        return None
    report_path = boe_path.parent / "skillspector.json"
    if not report_path.exists():
        return None
    report = json.loads(report_path.read_text())
    if not isinstance(report, dict):
        return None
    return {
        "boe": boe,
        "boe_path": boe_path,
        "report": report,
        "report_path": report_path,
        "scan_timestamp": str(scan_timestamp),
    }


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
    selected = select_scanner_run(scanner_runs)
    native_recommendation = selected["native_recommendation"] or "Unknown"
    recommendation = native_recommendation if native_recommendation in RECOMMENDATION_LABELS else "Unknown"
    return {
        "risk": selected["display_risk"],
        "reason": selected["display_risk_reason"],
        "recommendation": recommendation,
        "recommendation_label": recommendation_label(recommendation),
        "scan_mode": selected["scan_mode"],
        "confidence_flags": selected["confidence_flags"],
    }


def select_scanner_run(scanner_runs: list[dict[str, Any]]) -> dict[str, Any]:
    mode_rank = {"static-only": 0, "llm-assisted": 1}
    return max(
        scanner_runs,
        key=lambda row: (
            row.get("last_scanned") or "",
            mode_rank.get(row.get("scan_mode"), 0),
        ),
    )


def recommendation_label(recommendation: str) -> str:
    return RECOMMENDATION_LABELS.get(recommendation, "Unknown")


def scanner_provenance(scanner_run: dict[str, Any]) -> dict[str, Any]:
    return {
        "name": scanner_run.get("scanner_name"),
        "version": scanner_run.get("scanner_version"),
        "scan_mode": scanner_run.get("scan_mode"),
        "provider": scanner_run.get("llm_provider"),
        "model": scanner_run.get("llm_model"),
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
    return datetime.fromtimestamp(newest_mtime, tz=UTC).isoformat()


def skill_latest_source_commit_sha(skill) -> str:
    completed = subprocess.run(
        ["git", "log", "-1", "--format=%H", "--", skill.path.as_posix()],
        text=True,
        capture_output=True,
        check=False,
    )
    return completed.stdout.strip()


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
    return datetime.fromtimestamp(oldest_mtime, tz=UTC).isoformat()


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
