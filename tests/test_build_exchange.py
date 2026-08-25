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


def _fake_clean_report(*, llm_requested: bool = False, recommendation: str = "SAFE") -> dict:
    return {
        "metadata": {"llm_requested": llm_requested, "skillspector_version": "2.1.5"},
        "risk_assessment": {"score": 0, "severity": "LOW", "recommendation": recommendation},
        "issues": [],
    }


def _tracked_boe_fixture(monkeypatch, tmp_path: Path, *, mode: str = "static-only"):
    source_generated = tmp_path / "source-generated"

    def fake_run_skillspector(skill_path, output_path, *, no_llm):
        report = _fake_clean_report(llm_requested=not no_llm)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps(report))
        return report

    monkeypatch.setattr(exchange_builder, "skillspector_version", lambda: "2.1.5")
    monkeypatch.setattr(exchange_builder, "run_skillspector", fake_run_skillspector)
    monkeypatch.setattr(
        exchange_builder,
        "skillspector_llm_config",
        lambda: {"provider": "openai", "model": "gpt-5"},
    )
    build_exchange(
        skills_root=Path("tests/fixtures/skills"),
        exchange_dir=Path(".exchange"),
        generated_dir=source_generated,
        scan_modes=(mode,),
    )

    generated = tmp_path / "generated"
    shutil.copytree(source_generated / "boe", generated / "boe")
    boe_paths = list((generated / "boe").glob("*/*/*/*/boe.json"))
    assert len(boe_paths) == 1
    return generated, boe_paths[0].parent


def _write_bundle_json(bundle_dir: Path, filename: str, payload: dict) -> None:
    path = bundle_dir / filename
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    if filename == "hashes.json":
        return
    hashes_path = bundle_dir / "hashes.json"
    hashes = json.loads(hashes_path.read_text())
    hashes[filename] = sha256(path.read_bytes()).hexdigest()
    hashes_path.write_text(json.dumps(hashes, indent=2, sort_keys=True) + "\n")


def _assert_reuse_only_rejects(generated: Path, *, mode: str = "static-only") -> None:
    with pytest.raises(RuntimeError) as error:
        build_exchange(
            skills_root=Path("tests/fixtures/skills"),
            exchange_dir=Path(".exchange"),
            generated_dir=generated,
            scan_modes=(mode,),
            reuse_boe_only=True,
        )
    assert str(error.value) == f"missing tracked BOE for exact skill content: ai4sdlc/sample-skill ({mode})"


def test_build_exchange_writes_index_boe_and_zip(monkeypatch, tmp_path: Path):
    generated = tmp_path / "generated"

    def fake_run_skillspector(skill_path, output_path, *, no_llm):
        report = _fake_clean_report(llm_requested=not no_llm)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps(report))
        return report

    monkeypatch.setattr(exchange_builder, "skillspector_version", lambda: "2.1.5")
    monkeypatch.setattr(exchange_builder, "run_skillspector", fake_run_skillspector)

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


def test_build_exchange_reuses_tracked_boe_when_derived_outputs_are_absent(monkeypatch, tmp_path: Path):
    generated = tmp_path / "generated"
    calls = 0

    def fake_run_skillspector(skill_path, output_path, *, no_llm):
        nonlocal calls
        calls += 1
        report = _fake_clean_report(llm_requested=not no_llm)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps(report))
        return report

    monkeypatch.setattr(exchange_builder, "skillspector_version", lambda: "v2.1.5")
    monkeypatch.setattr(exchange_builder, "run_skillspector", fake_run_skillspector)

    first = build_exchange(
        skills_root=Path("tests/fixtures/skills"),
        exchange_dir=Path(".exchange"),
        generated_dir=generated,
        scan_modes=("static-only",),
    )
    assert first["reused_scans"] == 0
    assert calls == 1

    boe_only = tmp_path / "boe-only-generated"
    shutil.copytree(generated / "boe", boe_only / "boe")
    shutil.rmtree(generated)

    second_calls = 0

    def fail_if_scanner_runs(skill_path, output_path, *, no_llm):
        nonlocal second_calls
        second_calls += 1
        raise AssertionError("matching BOE should prevent another SkillSpector scan")

    monkeypatch.setattr(exchange_builder, "skillspector_version", lambda: "2.1.5")
    monkeypatch.setattr(exchange_builder, "run_skillspector", fail_if_scanner_runs)

    second = build_exchange(
        skills_root=Path("tests/fixtures/skills"),
        exchange_dir=Path(".exchange"),
        generated_dir=boe_only,
        scan_modes=("static-only",),
    )

    assert second["reused_scans"] == 1
    assert second_calls == 0
    index = json.loads((boe_only / "index.json").read_text())
    scanner_runs = json.loads((boe_only / "tables" / "scanner_runs.json").read_text())
    scanner_artifacts = json.loads((boe_only / "tables" / "scanner_artifacts.json").read_text())
    assert index["skills"][0]["display_id"] == "ai4sdlc/sample-skill"
    assert index["skills"][0]["scanner_run_ids"] == [scanner_runs["rows"][0]["id"]]
    assert Path(index["skills"][0]["boe_path"]).is_relative_to(boe_only / "boe")
    assert Path(scanner_runs["rows"][0]["native_report_path"]).exists()
    assert {row["artifact_kind"] for row in scanner_artifacts["rows"]} == {
        "boe",
        "native_report",
        "summary",
    }


def test_build_exchange_reuse_boe_only_never_calls_scanner_paths(monkeypatch, tmp_path: Path):
    source_generated = tmp_path / "source-generated"
    scanner_version = ["2.1.5"]

    def fake_run_skillspector(skill_path, output_path, *, no_llm):
        report = _fake_clean_report(llm_requested=not no_llm)
        report["metadata"]["skillspector_version"] = scanner_version[0]
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps(report))
        return report

    monkeypatch.setattr(exchange_builder, "skillspector_version", lambda: scanner_version[0])
    monkeypatch.setattr(
        exchange_builder,
        "skillspector_llm_config",
        lambda: {"provider": "openai", "model": "gpt-5"},
    )
    monkeypatch.setattr(exchange_builder, "run_skillspector", fake_run_skillspector)
    build_exchange(
        skills_root=Path("tests/fixtures/skills"),
        exchange_dir=Path(".exchange"),
        generated_dir=source_generated,
        scan_modes=("static-only", "llm-assisted"),
    )
    scanner_version[0] = "2.1.6"
    build_exchange(
        skills_root=Path("tests/fixtures/skills"),
        exchange_dir=Path(".exchange"),
        generated_dir=source_generated,
        scan_modes=("static-only",),
    )

    generated = tmp_path / "generated"
    shutil.copytree(source_generated / "boe", generated / "boe")

    def forbidden(*args, **kwargs):
        raise AssertionError("reuse-BOE-only generation must not enter a scanner or scanner-config path")

    monkeypatch.setattr(exchange_builder, "skillspector_version", forbidden)
    monkeypatch.setattr(exchange_builder, "scanner_cache_config", forbidden)
    monkeypatch.setattr(exchange_builder, "skillspector_llm_config", forbidden)
    monkeypatch.setattr(exchange_builder, "run_skillspector", forbidden)
    monkeypatch.setattr(exchange_builder, "write_boe", forbidden)

    result = build_exchange(
        skills_root=Path("tests/fixtures/skills"),
        exchange_dir=Path(".exchange"),
        generated_dir=generated,
        scan_modes=("static-only", "llm-assisted"),
        reuse_boe_only=True,
    )

    index = json.loads((generated / "index.json").read_text())
    scanner_runs = json.loads((generated / "tables" / "scanner_runs.json").read_text())["rows"]
    assert result == {"skills_written": 1, "reused_scans": 2, "invalid_skills": []}
    assert index["skills"][0]["display_id"] == "ai4sdlc/sample-skill"
    assert index["skills"][0]["scanner_provenance"] == {
        "name": "skillspector",
        "version": "2.1.6",
        "scan_mode": "static-only",
        "provider": None,
        "model": None,
    }
    assert len(scanner_runs) == 2
    llm_run = next(row for row in scanner_runs if row["scan_mode"] == "llm-assisted")
    assert llm_run["llm_provider"] == "openai"
    assert llm_run["llm_model"] == "gpt-5"
    assert (generated / "skills" / "ai4sdlc--sample-skill.json").exists()
    assert (generated / "zips" / "ai4sdlc--sample-skill.zip").exists()


def test_build_exchange_reuse_boe_only_fails_for_missing_exact_content(monkeypatch, tmp_path: Path):
    def forbidden(*args, **kwargs):
        raise AssertionError("missing BOE must fail before any scanner path")

    monkeypatch.setattr(exchange_builder, "skillspector_version", forbidden)
    monkeypatch.setattr(exchange_builder, "scanner_cache_config", forbidden)
    monkeypatch.setattr(exchange_builder, "skillspector_llm_config", forbidden)
    monkeypatch.setattr(exchange_builder, "run_skillspector", forbidden)
    monkeypatch.setattr(exchange_builder, "write_boe", forbidden)

    generated = tmp_path / "generated"
    with pytest.raises(RuntimeError) as error:
        build_exchange(
            skills_root=Path("tests/fixtures/skills"),
            exchange_dir=Path(".exchange"),
            generated_dir=generated,
            scan_modes=("static-only",),
            reuse_boe_only=True,
        )

    assert str(error.value) == (
        "missing tracked BOE for exact skill content: ai4sdlc/sample-skill (static-only)"
    )
    assert not (generated / "index.json").exists()


@pytest.mark.parametrize(
    ("metadata_field", "tampered_value"),
    (("skillspector_version", "9.9.9"), ("llm_requested", True)),
)
def test_build_exchange_reuse_boe_only_rejects_hash_valid_report_tampering(
    monkeypatch, tmp_path: Path, metadata_field: str, tampered_value
):
    generated, bundle_dir = _tracked_boe_fixture(monkeypatch, tmp_path)
    report = json.loads((bundle_dir / "skillspector.json").read_text())
    report["metadata"][metadata_field] = tampered_value
    _write_bundle_json(bundle_dir, "skillspector.json", report)

    _assert_reuse_only_rejects(generated)


def test_build_exchange_reuse_boe_only_rejects_hash_valid_config_tampering(monkeypatch, tmp_path: Path):
    generated, bundle_dir = _tracked_boe_fixture(monkeypatch, tmp_path)
    scanner_config = json.loads((bundle_dir / "scanner-config.json").read_text())
    scanner_config["native_output_format"] = "tampered"
    _write_bundle_json(bundle_dir, "scanner-config.json", scanner_config)

    _assert_reuse_only_rejects(generated)


def test_build_exchange_reuse_boe_only_rejects_hash_manifest_tampering(monkeypatch, tmp_path: Path):
    generated, bundle_dir = _tracked_boe_fixture(monkeypatch, tmp_path)
    hashes = json.loads((bundle_dir / "hashes.json").read_text())
    hashes["summary.json"] = "0" * 64
    _write_bundle_json(bundle_dir, "hashes.json", hashes)

    _assert_reuse_only_rejects(generated)


def test_build_exchange_reuse_boe_only_rejects_hash_valid_scan_key_tampering(monkeypatch, tmp_path: Path):
    generated, bundle_dir = _tracked_boe_fixture(monkeypatch, tmp_path)
    boe = json.loads((bundle_dir / "boe.json").read_text())
    tampered_key = f"{boe['scan_cache_key']}-tampered"
    boe["scan_cache_key"] = tampered_key
    _write_bundle_json(bundle_dir, "boe.json", boe)
    bundle_dir.rename(bundle_dir.with_name(tampered_key))

    _assert_reuse_only_rejects(generated)


def test_build_exchange_reuse_boe_only_rejects_hash_valid_provider_tampering(monkeypatch, tmp_path: Path):
    generated, bundle_dir = _tracked_boe_fixture(monkeypatch, tmp_path, mode="llm-assisted")
    boe = json.loads((bundle_dir / "boe.json").read_text())
    boe["provider"] = "tampered"
    _write_bundle_json(bundle_dir, "boe.json", boe)

    _assert_reuse_only_rejects(generated, mode="llm-assisted")


def test_build_exchange_reuse_boe_only_rejects_hash_valid_failed_scan(monkeypatch, tmp_path: Path):
    generated, bundle_dir = _tracked_boe_fixture(monkeypatch, tmp_path)
    report = exchange_builder.scanner_failure_report(
        mode="static-only",
        scanner_version="2.1.5",
        error=RuntimeError("scanner unavailable"),
    )
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

    _assert_reuse_only_rejects(generated)


def test_build_exchange_reuse_boe_only_rejects_hash_valid_summary_tampering(monkeypatch, tmp_path: Path):
    generated, bundle_dir = _tracked_boe_fixture(monkeypatch, tmp_path)
    summary = json.loads((bundle_dir / "summary.json").read_text())
    summary["risk"] = "High"
    _write_bundle_json(bundle_dir, "summary.json", summary)

    _assert_reuse_only_rejects(generated)


def test_build_exchange_reuse_boe_only_rejects_hash_valid_incomplete_assessment(
    monkeypatch, tmp_path: Path
):
    generated, bundle_dir = _tracked_boe_fixture(monkeypatch, tmp_path)
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

    _assert_reuse_only_rejects(generated)


def test_build_exchange_reuse_boe_only_rejects_symlinked_bundle_file(monkeypatch, tmp_path: Path):
    generated, bundle_dir = _tracked_boe_fixture(monkeypatch, tmp_path)
    summary_path = bundle_dir / "summary.json"
    summary_copy = bundle_dir.parent / "summary-copy.json"
    shutil.copyfile(summary_path, summary_copy)
    summary_path.unlink()
    try:
        summary_path.symlink_to(summary_copy)
    except OSError:
        pytest.skip("creating symlinks requires an unavailable Windows privilege")

    _assert_reuse_only_rejects(generated)


def test_build_exchange_blocks_invalid_required_metadata(monkeypatch, tmp_path: Path):
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
    calls = 0

    def fake_run_skillspector(skill_path, output_path, *, no_llm):
        nonlocal calls
        calls += 1
        return _fake_clean_report()

    monkeypatch.setattr(exchange_builder, "run_skillspector", fake_run_skillspector)

    result = build_exchange(
        skills_root=tmp_path / "skills",
        exchange_dir=Path(".exchange"),
        generated_dir=generated,
        scan_modes=("static-only",),
    )

    assert result["skills_written"] == 0
    assert result["invalid_skills"] == ["team/broken-skill"]
    assert calls == 0
    assert json.loads((generated / "index.json").read_text())["skills"] == []
    assert not (generated / "zips" / "team--broken-skill.zip").exists()


def test_build_exchange_records_unknown_when_scanner_fails(monkeypatch, tmp_path: Path):
    exchange_dir = tmp_path / "exchange"
    exchange_dir.mkdir()
    (exchange_dir / "categories.yaml").write_text("categories:\n  - id: testing\n    label: Testing\n")
    (exchange_dir / "tags.yaml").write_text("tags:\n  - tests\n  - example\n")
    (exchange_dir / "display-policy.yaml").write_text(
        "show_unknown_risk: true\nshow_confidence_flags: true\ndefault_sort: name\n"
    )
    generated = tmp_path / "generated"

    def failing_run_skillspector(skill_path, output_path, *, no_llm):
        raise RuntimeError("scanner unavailable")

    monkeypatch.setattr(exchange_builder, "skillspector_version", lambda: "2.1.5")
    monkeypatch.setattr(exchange_builder, "run_skillspector", failing_run_skillspector)

    result = build_exchange(
        skills_root=Path("tests/fixtures/skills"),
        exchange_dir=exchange_dir,
        generated_dir=generated,
        scan_modes=("static-only",),
    )

    index = json.loads((generated / "index.json").read_text())
    scanner_runs = json.loads((generated / "tables" / "scanner_runs.json").read_text())["rows"]
    assert result["skills_written"] == 1
    assert index["skills"][0]["risk"] == "Unknown"
    assert index["skills"][0]["recommendation"] == "Unknown"
    assert index["skills"][0]["recommendation_label"] == "Unknown"
    assert "scanner_failed" in index["skills"][0]["risk_reason"]
    assert scanner_runs[0]["status"] == "failed"
    assert scanner_runs[0]["display_risk"] == "Unknown"


def test_build_exchange_reuses_cached_scan_without_running_skillspector(monkeypatch, tmp_path: Path):
    generated = tmp_path / "generated"
    calls = 0

    def fake_run_skillspector(skill_path, output_path, *, no_llm):
        nonlocal calls
        calls += 1
        output_path.parent.mkdir(parents=True, exist_ok=True)
        report = {
            "metadata": {"llm_requested": False, "skillspector_version": "2.1.5"},
            "risk_assessment": {"score": 0, "severity": "LOW", "recommendation": "SAFE"},
            "issues": [],
        }
        output_path.write_text(json.dumps(report))
        return report

    monkeypatch.setattr(exchange_builder, "skillspector_version", lambda: "2.1.5")
    monkeypatch.setattr(exchange_builder, "run_skillspector", fake_run_skillspector)

    first = build_exchange(
        skills_root=Path("tests/fixtures/skills"),
        exchange_dir=Path(".exchange"),
        generated_dir=generated,
        scan_modes=("static-only",),
    )
    second = build_exchange(
        skills_root=Path("tests/fixtures/skills"),
        exchange_dir=Path(".exchange"),
        generated_dir=generated,
        scan_modes=("static-only",),
    )

    scanner_runs = json.loads((generated / "tables" / "scanner_runs.json").read_text())["rows"]
    assert first["reused_scans"] == 0
    assert second["reused_scans"] == 1
    assert calls == 1
    assert len(scanner_runs) == 1


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


def test_recommendation_labels_are_plain_language():
    assert exchange_builder.recommendation_label("SAFE") == "Safe to use"
    assert exchange_builder.recommendation_label("CAUTION") == "Use caution"
    assert exchange_builder.recommendation_label("DO_NOT_INSTALL") == "Avoid installing"
    assert exchange_builder.recommendation_label("Unknown") == "Unknown"
