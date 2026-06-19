import json
from datetime import datetime
from pathlib import Path

from skill_exchange import exchange_builder
from skill_exchange.exchange_builder import aggregate_assessment, build_exchange, make_scan_key, scanner_finding_rows_for


def test_build_exchange_writes_index_boe_and_zip(tmp_path: Path):
    generated = tmp_path / "generated"

    result = build_exchange(
        skills_root=Path("tests/fixtures/skills"),
        exchange_dir=Path(".exchange"),
        generated_dir=generated,
        scan_modes=("static-only",),
    )

    assert result["skills_written"] == 1
    index = json.loads((generated / "index.json").read_text())
    assert index["skills"][0]["display_id"] == "ai4sdlc/sample-skill"
    assert "risk" not in index["skills"][0]
    assert "risk_reason" not in index["skills"][0]
    assert index["skills"][0]["recommendation"] == "SAFE"
    assert "Low confidence" in index["skills"][0]["confidence_flags"]
    assert index["skills"][0]["skill_files"] == [{"path": "SKILL.md", "size_bytes": 290}]
    assert "# Sample Skill" in index["skills"][0]["skill_md_content"]
    assert index["skills"][0]["source_url"].endswith("/tree/main/tests/fixtures/skills/ai4sdlc/sample-skill")
    assert datetime.fromisoformat(index["skills"][0]["last_updated"])
    assert datetime.fromisoformat(index["skills"][0]["first_observed"])
    assert datetime.fromisoformat(index["skills"][0]["last_scanned"])
    assert index["skills"][0]["scan_mode"] == "static-only"
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
        "scan_mode": "llm-assisted",
        "confidence_flags": [],
    }
