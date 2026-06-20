from __future__ import annotations

import json
import os
import shutil
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from .models import SkillPackage, ValidationResult


def report_metadata(report: dict[str, Any]) -> dict[str, Any]:
    metadata = report.get("metadata")
    return metadata if isinstance(metadata, dict) else {}


def write_boe(
    *,
    root: Path,
    skill: SkillPackage,
    scan_key: str,
    report: dict[str, Any],
    assessment: dict[str, Any],
    validation: ValidationResult,
    report_path: Path,
    source_commit_sha: str | None = None,
    scan_timestamp: str | None = None,
    scanner_config: dict[str, Any] | None = None,
) -> Path:
    boe_dir = root / "boe" / skill.metadata.namespace / skill.metadata.skill_id / skill.content_hash / scan_key
    boe_dir.mkdir(parents=True, exist_ok=True)
    skillspector_path = boe_dir / "skillspector.json"
    summary_path = boe_dir / "summary.json"
    boe_path = boe_dir / "boe.json"
    metadata = report_metadata(report)
    scanner_config = scanner_config or {}

    shutil.copyfile(report_path, skillspector_path)
    summary = {
        "risk": assessment["risk"],
        "risk_reason": assessment["reason"],
        "confidence_flags": assessment["confidence_flags"],
    }
    summary_path.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n")
    boe = {
        "schema_version": "skill-exchange-boe/v0",
        "namespace": skill.metadata.namespace,
        "skill_id": skill.metadata.skill_id,
        "display_id": skill.metadata.display_id,
        "skill_path": skill.path.as_posix(),
        "source_commit_sha": source_commit_sha,
        "skill_content_hash": skill.content_hash,
        "scan_cache_key": scan_key,
        "scanner": {
            "name": "skillspector",
            "version": metadata.get("skillspector_version", "unknown"),
        },
        "scan_mode": "static-only" if metadata.get("llm_requested") is False else "llm-assisted",
        "provider": scanner_config.get("llm_provider"),
        "model": scanner_config.get("llm_model"),
        "scan_timestamp": scan_timestamp,
        "generated_at": datetime.now(UTC).isoformat(),
        "pipeline": {
            "id": os.environ.get("CI_PIPELINE_ID"),
            "job_id": os.environ.get("CI_JOB_ID"),
        },
        "risk": assessment["risk"],
        "risk_reason": assessment["reason"],
        "confidence_flags": assessment["confidence_flags"],
        "validation_warnings": list(validation.warnings),
        "metadata_flags": list(validation.metadata_flags),
        "paths": {
            "skillspector": skillspector_path.as_posix(),
            "summary": summary_path.as_posix(),
            "report_source": report_path.as_posix(),
        },
    }
    boe_path.write_text(json.dumps(boe, indent=2, sort_keys=True) + "\n")
    return boe_path
