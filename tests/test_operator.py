import json
import subprocess
from pathlib import Path

from skill_assessment.cli import main as assessment
from skill_exchange.operator import main
from test_assessment_advice import gateway as gateway
from test_assessment_advice import scanner as scanner
from test_assessment_advice import skill as skill

REAL_RUN = subprocess.run


def test_assessment_index_builds_site_without_reassessment(skill, scanner, tmp_path, monkeypatch):
    catalog = tmp_path / "skills" / "customer"
    catalog.mkdir(parents=True)
    skill = skill.rename(catalog / skill.name)
    evidence = tmp_path / "evidence"
    directory = evidence / "customer" / skill.name
    scanner["report"]["metadata"].update(llm_requested=False, skillspector_version="2.10.0")
    scanner["report"]["risk_assessment"]["recommendation"] = "CAUTION"
    args = ["assess", "--skill", str(skill), "--output-dir", str(directory), "--scan-mode", "static-only"]
    assert assessment(args) == 0
    (skill / "SKILL.md").write_text((skill / "SKILL.md").read_text() + "Updated instructions")
    scanner["report"]["risk_assessment"]["score"] = 60
    assert assessment(args) == 0
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
    assert records[0]["scanner_provenance"]["version"] == "2.10.0"
    assert (generated / "zips/customer--my-skill.zip").is_file()
    artifacts = json.loads((generated / "tables/scanner_artifacts.json").read_text())["rows"]
    native = next(item for item in artifacts if item["artifact_kind"] == "native_report")
    assert json.loads(Path(native["path"]).read_text()) == scanner["report"]
    assert before == {p: p.read_bytes() for p in evidence.rglob("*") if p.is_file()}
