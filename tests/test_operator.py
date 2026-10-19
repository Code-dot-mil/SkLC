import json
import subprocess
from pathlib import Path

import pytest
from skill_assessment.cli import main as assessment
from skill_assessment.commands.verify_boe import verify_boe
from skill_exchange.exchange_builder import build_exchange
from skill_exchange.operator import read_assessment_boe
from test_assessment_advice import gateway as gateway
from test_assessment_advice import scanner as scanner
from test_assessment_advice import skill as skill

REAL_RUN = subprocess.run


@pytest.mark.parametrize("change", [None, "skill", "report", "missing", "path", "digests", "schema", "duplicate"])
def test_verify_current_evidence_offline(skill, scanner, tmp_path, capsys, change):
    output = tmp_path / "evidence"
    assert assessment(["assess", "--skill", str(skill), "--output-dir", str(output)]) == 0
    index_path = output / "index.json"
    index = json.loads(index_path.read_text())
    entry = index["assessments"][0]
    report = output / entry["path"] / "skillspector.json"
    if change == "skill":
        (skill / "SKILL.md").write_text((skill / "SKILL.md").read_text() + "Changed content")
    elif change == "report":
        report.write_text("{}")
    elif change == "missing":
        report.unlink()
    elif change == "path":
        entry["path"] = "../outside"
    elif change == "digests":
        entry.pop("reports")
    elif change == "schema":
        index["boe_schema_version"] = 99
    elif change == "duplicate":
        index["assessments"].append(entry.copy())
    index_path.write_text(json.dumps(index))
    before = {p: p.read_bytes() for p in output.rglob("*") if p.is_file()}
    calls = len(scanner["calls"])
    capsys.readouterr()
    assert assessment(["verify-boe", "--skill", str(skill), "--boe-dir", str(output)]) == bool(change)
    result = capsys.readouterr()
    if change is None:
        assert json.loads(result.out) == entry
    else:
        assert "Invalid BOE" in result.err
    assert len(scanner["calls"]) == calls
    assert before == {p: p.read_bytes() for p in output.rglob("*") if p.is_file()}


def test_assessment_index_builds_site_without_reassessment(skill, scanner, tmp_path, monkeypatch):
    catalog = tmp_path / "skills" / "customer"
    catalog.mkdir(parents=True)
    skill = skill.rename(catalog / skill.name)
    evidence = tmp_path / "evidence"
    directory = evidence / "customer" / skill.name
    scanner["report"]["metadata"].update(llm_requested=False, skillspector_version="2.10.0")
    scanner["report"]["risk_assessment"]["recommendation"] = "CAUTION"
    assert assessment(["assess", "--skill", str(skill), "--output-dir", str(directory),
                       "--scan-mode", "static-only"]) == 0
    before = {p: p.read_bytes() for p in evidence.rglob("*") if p.is_file()}
    calls = len(scanner["calls"])

    def run(command, **kwargs):
        if command[0] == "git":
            return REAL_RUN(command, **kwargs)
        assert command[:2] == ["skill-assessment", "verify-boe"]
        entry = verify_boe(Path(command[3]), Path(command[5]))
        return subprocess.CompletedProcess(command, 0, stdout=json.dumps(entry))

    monkeypatch.setattr(subprocess, "run", run)
    generated = tmp_path / "generated"
    options = dict(skills_root=tmp_path / "skills", exchange_dir=Path(".exchange"),
                   generated_dir=generated, boe_dir=evidence, boe_reader=read_assessment_boe)
    assert build_exchange(**options, scan_modes=("static-only",))["skills_written"] == 1
    records = json.loads((generated / "index.json").read_text())["skills"]
    assert records[0]["display_id"] == "customer/my-skill"
    assert records[0]["scanner_provenance"]["version"] == "2.10.0"
    assert (generated / "zips/customer--my-skill.zip").is_file()
    artifacts = json.loads((generated / "tables/scanner_artifacts.json").read_text())["rows"]
    native = next(item for item in artifacts if item["artifact_kind"] == "native_report")
    assert json.loads(Path(native["path"]).read_text()) == scanner["report"]
    assert before == {p: p.read_bytes() for p in evidence.rglob("*") if p.is_file()}
    assert len(scanner["calls"]) == calls
    with pytest.raises(ValueError, match="wrong scan mode"):
        build_exchange(**options, scan_modes=("llm-assisted",))
    (skill / "SKILL.md").write_text((skill / "SKILL.md").read_text() + "Changed")
    with pytest.raises(ValueError, match="current skill contents"):
        build_exchange(**options, scan_modes=("static-only",))
