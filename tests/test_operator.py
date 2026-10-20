import json
import subprocess
from pathlib import Path

from skill_exchange.operator import main

REAL_RUN = subprocess.run


def test_flat_assessment_builds_site_without_reassessment(tmp_path, monkeypatch):
    catalog = tmp_path / "skills" / "customer"
    catalog.mkdir(parents=True)
    skill = catalog / "my-skill"
    skill.mkdir()
    (skill / "SKILL.md").write_text("---\nname: my-skill\ndescription: Example\n---\nInstructions.\n")
    evidence = tmp_path / "evidence"
    directory = evidence / "customer" / skill.name
    directory.mkdir(parents=True)
    report = {
        "execution_successful": True, "issues": [],
        "analysis_completeness": {"is_complete": True},
        "metadata": {"llm_requested": False, "skillspector_version": "2.12.0"},
        "risk_assessment": {"score": 0, "severity": "LOW", "recommendation": "SAFE"},
    }
    (directory / "skillspector.json").write_text(json.dumps(report))
    (directory / "adjudication.json").write_text(json.dumps({
        "status": "not_performed", "safe_to_use": None, "findings": [],
        "metadata": {"created_at": "2026-10-20T12:00:00+00:00"},
    }))
    before = {p: p.read_bytes() for p in evidence.rglob("*") if p.is_file()}

    def run(command, **kwargs):
        assert command[0] == "git", "Generation must not invoke assessment commands or a scanner"
        return REAL_RUN(command, **kwargs)

    monkeypatch.setattr(subprocess, "run", run)
    generated = tmp_path / "generated"
    monkeypatch.setattr("sys.argv", ["operator", "generate", "--skills", str(tmp_path / "skills"),
                                    "--evidence", str(evidence), "--generated", str(generated),
                                    "--scan-mode", "static-only"])
    main()
    records = json.loads((generated / "index.json").read_text())["skills"]
    assert records[0]["display_id"] == "customer/my-skill"
    assert records[0]["scanner_provenance"]["version"] == "2.12.0"
    assert (generated / "zips/customer--my-skill.zip").is_file()
    artifacts = json.loads((generated / "tables/scanner_artifacts.json").read_text())["rows"]
    native = next(item for item in artifacts if item["artifact_kind"] == "native_report")
    assert json.loads(Path(native["path"]).read_text()) == report
    assert before == {p: p.read_bytes() for p in evidence.rglob("*") if p.is_file()}
