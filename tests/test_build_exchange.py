import json
import shutil
from datetime import datetime
from hashlib import sha256
from pathlib import Path

import pytest
from skill_exchange import exchange_builder
from skill_exchange.exchange_builder import (
    aggregate_assessment,
    build_exchange,
    make_scan_key,
    scanner_finding_rows_for,
)
from skill_exchange.skills import discover_skills


def _fake_clean_report(*, llm_requested: bool = False, recommendation: str = "SAFE") -> dict:
    return {
        "metadata": {"llm_requested": llm_requested, "skillspector_version": "2.1.5"},
        "risk_assessment": {"score": 0, "severity": "LOW", "recommendation": recommendation},
        "issues": [],
    }


def _tracked_boe_fixture(tmp_path: Path, *, mode: str = "static-only"):
    skill = discover_skills(Path("tests/fixtures/skills"))[0]
    report = _fake_clean_report(llm_requested=mode == "llm-assisted")
    config = {"native_output_format": "skillspector-json-v2", "scan_mode": mode}
    if mode == "llm-assisted":
        config.update(llm_provider="openai", llm_model="gpt-5")
    scan_key = make_scan_key(
        namespace=skill.metadata.namespace, skill_id=skill.metadata.skill_id,
        content_hash=skill.content_hash, scanner_version="2.1.5", mode=mode, scanner_config=config,
    )
    generated = tmp_path / "generated"
    bundle = generated / "boe" / "ai4sdlc" / "sample-skill" / skill.content_hash / scan_key
    bundle.mkdir(parents=True, exist_ok=True)
    summary = {
        "risk": "Low", "risk_reason": "No medium, high, or critical findings detected.",
        "confidence_flags": ["Low confidence"] if mode == "static-only" else [],
    }
    boe = {
        "schema_version": "skill-exchange-boe/v0", "namespace": "ai4sdlc", "skill_id": "sample-skill",
        "display_id": "ai4sdlc/sample-skill", "skill_content_hash": skill.content_hash,
        "scan_cache_key": scan_key, "scanner": {"name": "skillspector", "version": "2.1.5"},
        "scan_mode": mode, "provider": config.get("llm_provider"), "model": config.get("llm_model"),
        "scan_timestamp": "2026-09-01T00:00:00+00:00", **summary,
    }
    files = {"boe.json": boe, "summary.json": summary, "scanner-config.json": config, "skillspector.json": report}
    for name, value in files.items():
        (bundle / name).write_text(json.dumps(value))
    (bundle / "hashes.json").write_text(json.dumps({
        name: sha256((bundle / name).read_bytes()).hexdigest() for name in files
    }))
    return generated, bundle


def _write_bundle_json(bundle_dir: Path, filename: str, payload: dict) -> None:
    path = bundle_dir / filename
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    if filename == "hashes.json":
        return
    hashes_path = bundle_dir / "hashes.json"
    hashes = json.loads(hashes_path.read_text())
    hashes[filename] = sha256(path.read_bytes()).hexdigest()
    hashes_path.write_text(json.dumps(hashes, indent=2, sort_keys=True) + "\n")


def _assert_evidence_rejected(generated: Path, *, mode: str = "static-only") -> None:
    with pytest.raises(RuntimeError) as error:
        build_exchange(
            skills_root=Path("tests/fixtures/skills"),
            exchange_dir=Path(".exchange"),
            generated_dir=generated,
            scan_modes=(mode,),
        )
    assert str(error.value) == f"missing tracked BOE for exact skill content: ai4sdlc/sample-skill ({mode})"


def test_build_exchange_writes_site_data_without_changing_evidence(tmp_path: Path):
    generated, bundle = _tracked_boe_fixture(tmp_path)
    original = {p.name: p.read_bytes() for p in bundle.iterdir()}

    result = build_exchange(
        skills_root=Path("tests/fixtures/skills"),
        exchange_dir=Path(".exchange"),
        generated_dir=generated,
        scan_modes=("static-only",),
    )

    assert result["skills_written"] == 1
    index = json.loads((generated / "index.json").read_text())
    assert index["skills"][0]["display_id"] == "ai4sdlc/sample-skill"
    assert index["skills"][0]["risk"] == "Low"
    assert index["skills"][0]["risk_reason"] == "No medium, high, or critical findings detected."
    assert index["skills"][0]["recommendation"] == "SAFE"
    assert index["skills"][0]["recommendation_label"] == "Safe to use"
    assert "Low confidence" in index["skills"][0]["confidence_flags"]
    assert index["skills"][0]["skill_files"] == [{"path": "SKILL.md", "size_bytes": 290}]
    assert "# Sample Skill" in index["skills"][0]["skill_md_content"]
    assert index["skills"][0]["source_url"].endswith("/tree/main/tests/fixtures/skills/ai4sdlc/sample-skill")
    assert datetime.fromisoformat(index["skills"][0]["last_updated"])
    assert datetime.fromisoformat(index["skills"][0]["first_observed"])
    assert datetime.fromisoformat(index["skills"][0]["last_scanned"])
    assert len(index["skills"][0]["latest_source_commit_sha"]) in {0, 40}
    assert index["skills"][0]["scan_mode"] == "static-only"
    assert index["skills"][0]["scanner_provenance"] == {
        "name": "skillspector",
        "version": "2.1.5",
        "scan_mode": "static-only",
        "provider": None,
        "model": None,
    }
    assert "/boe/" in index["skills"][0]["boe_path"]
    boe_dir = Path(index["skills"][0]["boe_path"]).parent
    scanner_config = json.loads((boe_dir / "scanner-config.json").read_text())
    support_hashes = json.loads((boe_dir / "hashes.json").read_text())
    assert scanner_config == {"native_output_format": "skillspector-json-v2", "scan_mode": "static-only"}
    assert support_hashes["skillspector.json"]
    assert support_hashes["summary.json"]
    assert (generated / "zips" / "ai4sdlc--sample-skill.zip").exists()
    assert index["skills"][0]["download_path"] == "downloads/ai4sdlc--sample-skill.zip"
    detail = json.loads((generated / "skills" / "ai4sdlc--sample-skill.json").read_text())
    skills_table = json.loads((generated / "tables" / "skills.json").read_text())
    assert detail["download_path"] == index["skills"][0]["download_path"]
    assert skills_table["rows"][0]["download_path"] == detail["download_path"]
    scanner_runs = json.loads((generated / "tables" / "scanner_runs.json").read_text())
    scanner_artifacts = json.loads((generated / "tables" / "scanner_artifacts.json").read_text())
    scanner_findings = json.loads((generated / "tables" / "scanner_findings.json").read_text())
    assert scanner_runs["rows"][0]["scanner_name"] == "skillspector"
    assert scanner_runs["rows"][0]["native_output_format"] == "skillspector-json-v2"
    assert scanner_runs["rows"][0]["native_report_path"].endswith("/skillspector.json")
    assert scanner_runs["rows"][0]["scan_cache_key"]
    assert scanner_runs["rows"][0]["content_hash"] == index["skills"][0]["content_hash"]
    assert scanner_runs["rows"][0]["last_scanned"] == index["skills"][0]["last_scanned"]
    native_artifact = next(row for row in scanner_artifacts["rows"] if row["artifact_kind"] == "native_report")
    assert native_artifact["download_path"].endswith("/skillspector.json")
    assert {row["download_path"] for row in scanner_artifacts["rows"]} == {
        f"downloads/scanner-runs/{scanner_runs['rows'][0]['id']}/{filename}"
        for filename in ("skillspector.json", "summary.json", "boe.json")
    }
    assert all(Path(row["path"]).is_file() for row in scanner_artifacts["rows"])
    assert scanner_findings["rows"] == []

    second = build_exchange(
        skills_root=Path("tests/fixtures/skills"),
        exchange_dir=Path(".exchange"),
        generated_dir=generated,
        scan_modes=("static-only",),
    )
    assert second["reused_scans"] == 1
    scanner_runs = json.loads((generated / "tables" / "scanner_runs.json").read_text())
    index = json.loads((generated / "index.json").read_text())
    assert len(scanner_runs["rows"]) == 1
    assert len(index["skills"][0]["scanner_run_ids"]) == 1
    assert index["skills"][0]["scanner_run_ids"][0] == scanner_runs["rows"][0]["id"]


    assert {p.name: p.read_bytes() for p in bundle.iterdir()} == original

def test_build_exchange_removes_stale_skill_zips(tmp_path: Path):
    generated, _bundle = _tracked_boe_fixture(tmp_path)
    zip_dir = generated / "zips"
    zip_dir.mkdir(parents=True)
    (zip_dir / "ai4sdlc--removed-skill.zip").write_bytes(b"stale")

    build_exchange(
        skills_root=Path("tests/fixtures/skills"),
        exchange_dir=Path(".exchange"),
        generated_dir=generated,
        scan_modes=("static-only",),
    )

    assert sorted(path.name for path in zip_dir.iterdir()) == ["ai4sdlc--sample-skill.zip"]


def test_build_exchange_fails_for_missing_exact_content(tmp_path: Path):
    generated = tmp_path / "generated"
    with pytest.raises(RuntimeError) as error:
        build_exchange(
            skills_root=Path("tests/fixtures/skills"),
            exchange_dir=Path(".exchange"),
            generated_dir=generated,
            scan_modes=("static-only",),
        )

    assert str(error.value) == (
        "missing tracked BOE for exact skill content: ai4sdlc/sample-skill (static-only)"
    )
    assert not (generated / "index.json").exists()


@pytest.mark.parametrize(
    ("metadata_field", "tampered_value"),
    (("skillspector_version", "9.9.9"), ("llm_requested", True)),
)
def test_build_exchange_rejects_hash_valid_report_tampering(
    tmp_path: Path, metadata_field: str, tampered_value
):
    generated, bundle_dir = _tracked_boe_fixture(tmp_path)
    report = json.loads((bundle_dir / "skillspector.json").read_text())
    report["metadata"][metadata_field] = tampered_value
    _write_bundle_json(bundle_dir, "skillspector.json", report)

    _assert_evidence_rejected(generated)


def test_build_exchange_rejects_hash_valid_config_tampering(tmp_path: Path):
    generated, bundle_dir = _tracked_boe_fixture(tmp_path)
    scanner_config = json.loads((bundle_dir / "scanner-config.json").read_text())
    scanner_config["native_output_format"] = "tampered"
    _write_bundle_json(bundle_dir, "scanner-config.json", scanner_config)

    _assert_evidence_rejected(generated)


def test_build_exchange_rejects_hash_manifest_tampering(tmp_path: Path):
    generated, bundle_dir = _tracked_boe_fixture(tmp_path)
    hashes = json.loads((bundle_dir / "hashes.json").read_text())
    hashes["summary.json"] = "0" * 64
    _write_bundle_json(bundle_dir, "hashes.json", hashes)

    _assert_evidence_rejected(generated)


def test_build_exchange_rejects_hash_valid_scan_key_tampering(tmp_path: Path):
    generated, bundle_dir = _tracked_boe_fixture(tmp_path)
    boe = json.loads((bundle_dir / "boe.json").read_text())
    tampered_key = f"{boe['scan_cache_key']}-tampered"
    boe["scan_cache_key"] = tampered_key
    _write_bundle_json(bundle_dir, "boe.json", boe)
    bundle_dir.rename(bundle_dir.with_name(tampered_key))

    _assert_evidence_rejected(generated)


def test_build_exchange_rejects_hash_valid_provider_tampering(tmp_path: Path):
    generated, bundle_dir = _tracked_boe_fixture(tmp_path, mode="llm-assisted")
    boe = json.loads((bundle_dir / "boe.json").read_text())
    boe["provider"] = "tampered"
    _write_bundle_json(bundle_dir, "boe.json", boe)

    _assert_evidence_rejected(generated, mode="llm-assisted")


def test_build_exchange_rejects_hash_valid_failed_scan(tmp_path: Path):
    generated, bundle_dir = _tracked_boe_fixture(tmp_path)
    report = {"metadata": {"scan_error": "scanner unavailable"}, "execution_successful": False}
    assessment = exchange_builder.assess_report(report)
    summary = {
        "risk": assessment["risk"],
        "risk_reason": assessment["reason"],
        "confidence_flags": assessment["confidence_flags"],
    }
    boe = json.loads((bundle_dir / "boe.json").read_text())
    boe["risk"] = assessment["risk"]
    boe["risk_reason"] = assessment["reason"]
    boe["confidence_flags"] = assessment["confidence_flags"]
    _write_bundle_json(bundle_dir, "skillspector.json", report)
    _write_bundle_json(bundle_dir, "summary.json", summary)
    _write_bundle_json(bundle_dir, "boe.json", boe)

    _assert_evidence_rejected(generated)


def test_build_exchange_rejects_hash_valid_summary_tampering(tmp_path: Path):
    generated, bundle_dir = _tracked_boe_fixture(tmp_path)
    summary = json.loads((bundle_dir / "summary.json").read_text())
    summary["risk"] = "High"
    _write_bundle_json(bundle_dir, "summary.json", summary)

    _assert_evidence_rejected(generated)


def test_build_exchange_rejects_hash_valid_incomplete_assessment(
    tmp_path: Path
):
    generated, bundle_dir = _tracked_boe_fixture(tmp_path)
    report = json.loads((bundle_dir / "skillspector.json").read_text())
    report["risk_assessment"] = {}
    assessment = exchange_builder.assess_report(report)
    summary = {
        "risk": assessment["risk"],
        "risk_reason": assessment["reason"],
        "confidence_flags": assessment["confidence_flags"],
    }
    boe = json.loads((bundle_dir / "boe.json").read_text())
    boe["risk"] = assessment["risk"]
    boe["risk_reason"] = assessment["reason"]
    boe["confidence_flags"] = assessment["confidence_flags"]
    _write_bundle_json(bundle_dir, "skillspector.json", report)
    _write_bundle_json(bundle_dir, "summary.json", summary)
    _write_bundle_json(bundle_dir, "boe.json", boe)

    _assert_evidence_rejected(generated)


def test_build_exchange_rejects_symlinked_bundle_file(tmp_path: Path):
    generated, bundle_dir = _tracked_boe_fixture(tmp_path)
    summary_path = bundle_dir / "summary.json"
    summary_copy = bundle_dir.parent / "summary-copy.json"
    shutil.copyfile(summary_path, summary_copy)
    summary_path.unlink()
    try:
        summary_path.symlink_to(summary_copy)
    except OSError:
        pytest.skip("creating symlinks requires an unavailable Windows privilege")

    _assert_evidence_rejected(generated)


def test_build_exchange_blocks_invalid_required_metadata(tmp_path: Path):
    skill_dir = tmp_path / "skills" / "team" / "broken-skill"
    skill_dir.mkdir(parents=True)
    (skill_dir / "SKILL.md").write_text(
        """---
name: wrong-name
description: ""
metadata:
  ai4sdlc.category: testing
---

# Broken
"""
    )
    generated = tmp_path / "generated"
    result = build_exchange(
        skills_root=tmp_path / "skills",
        exchange_dir=Path(".exchange"),
        generated_dir=generated,
        scan_modes=("static-only",),
    )

    assert result["skills_written"] == 0
    assert result["invalid_skills"] == ["team/broken-skill"]
    assert json.loads((generated / "index.json").read_text())["skills"] == []
    assert not (generated / "zips" / "team--broken-skill.zip").exists()


def test_scan_cache_key_includes_skill_identity_model_and_config_hash():
    static_key = make_scan_key(
        namespace="ai4sdlc",
        skill_id="sample-skill",
        content_hash="abc123",
        scanner_version="2.1.5",
        mode="static-only",
        scanner_config={"scan_mode": "static-only"},
    )
    llm_key = make_scan_key(
        namespace="ai4sdlc",
        skill_id="sample-skill",
        content_hash="abc123",
        scanner_version="2.1.5",
        mode="llm-assisted",
        scanner_config={"scan_mode": "llm-assisted", "llm_provider": "openai", "llm_model": "gpt-5"},
    )
    other_model_key = make_scan_key(
        namespace="ai4sdlc",
        skill_id="sample-skill",
        content_hash="abc123",
        scanner_version="2.1.5",
        mode="llm-assisted",
        scanner_config={"scan_mode": "llm-assisted", "llm_provider": "openai", "llm_model": "gpt-5.1"},
    )

    assert static_key.startswith("ai4sdlc--sample-skill--abc123--skillspector-2.1.5--static-only--")
    assert llm_key.startswith("ai4sdlc--sample-skill--abc123--skillspector-2.1.5--llm-assisted--")
    assert "--openai-gpt-5--" in llm_key
    assert static_key != llm_key
    assert llm_key != other_model_key


def test_scanner_finding_rows_preserve_native_details_for_display():
    rows = scanner_finding_rows_for(
        "run-1",
        {
            "issues": [
                {
                    "id": "AST1",
                    "category": "Dangerous Code Execution",
                    "pattern": "exec() call detected",
                    "severity": "HIGH",
                    "confidence": 0.85,
                    "location": {"file": "examples/demo.py", "start_line": 10, "end_line": 10},
                    "explanation": "exec() call detected",
                    "remediation": "Replace exec() with explicit parsing.",
                    "code_snippet": "exec(user_value)",
                }
            ]
        },
    )

    assert rows == [
        {
            "id": "run-1:AST1:0",
            "scanner_run_id": "run-1",
            "native_issue_id": "AST1",
            "severity": "HIGH",
            "category": "Dangerous Code Execution",
            "pattern": "exec() call detected",
            "confidence": 0.85,
            "path": "examples/demo.py",
            "start_line": 10,
            "end_line": 10,
            "explanation": "exec() call detected",
            "remediation": "Replace exec() with explicit parsing.",
            "code_snippet": "exec(user_value)",
            "native_finding_json": {
                "id": "AST1",
                "category": "Dangerous Code Execution",
                "pattern": "exec() call detected",
                "severity": "HIGH",
                "confidence": 0.85,
                "location": {"file": "examples/demo.py", "start_line": 10, "end_line": 10},
                "explanation": "exec() call detected",
                "remediation": "Replace exec() with explicit parsing.",
                "code_snippet": "exec(user_value)",
            },
        }
    ]


def test_aggregate_assessment_uses_latest_llm_assisted_scan_without_static_confidence_flag():
    assessment = aggregate_assessment(
        [
            {
                "scan_mode": "static-only",
                "last_scanned": "2026-06-19T21:00:00+00:00",
                "display_risk": "High",
                "display_risk_reason": "Critical or high severity finding detected.",
                "native_recommendation": "DO_NOT_INSTALL",
                "confidence_flags": ["Low confidence"],
            },
            {
                "scan_mode": "llm-assisted",
                "last_scanned": "2026-06-19T21:01:00+00:00",
                "display_risk": "Low",
                "display_risk_reason": "No medium, high, or critical findings detected.",
                "native_recommendation": "SAFE",
                "confidence_flags": [],
            },
        ]
    )

    assert assessment == {
        "risk": "Low",
        "reason": "No medium, high, or critical findings detected.",
        "recommendation": "SAFE",
        "recommendation_label": "Safe to use",
        "scan_mode": "llm-assisted",
        "confidence_flags": [],
    }


def test_aggregate_assessment_rejects_removed_review_recommendation():
    assessment = aggregate_assessment(
        [
            {
                "scan_mode": "static-only",
                "last_scanned": "2026-06-19T21:00:00+00:00",
                "display_risk": "Medium",
                "display_risk_reason": "Medium severity finding detected.",
                "native_recommendation": "REVIEW",
                "confidence_flags": [],
            }
        ]
    )

    assert assessment["recommendation"] == "Unknown"
    assert assessment["recommendation_label"] == "Unknown"


def test_recommendation_labels_are_plain_language():
    assert exchange_builder.recommendation_label("SAFE") == "Safe to use"
    assert exchange_builder.recommendation_label("CAUTION") == "Use caution"
    assert exchange_builder.recommendation_label("DO_NOT_INSTALL") == "Avoid installing"
    assert exchange_builder.recommendation_label("Unknown") == "Unknown"


def test_build_exchange_reads_separate_evidence_directory(tmp_path: Path):
    source, bundle = _tracked_boe_fixture(tmp_path)
    before = {p.name: p.read_bytes() for p in bundle.iterdir()}
    output = tmp_path / "local-generated"
    result = build_exchange(
        skills_root=Path("tests/fixtures/skills"), exchange_dir=Path(".exchange"),
        generated_dir=output, boe_dir=source / "boe", scan_modes=("static-only",),
    )
    assert result["skills_written"] == 1
    assert (output / "index.json").is_file()
    assert not (output / "boe").exists()
    assert {p.name: p.read_bytes() for p in bundle.iterdir()} == before
