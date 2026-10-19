import json
import subprocess
from datetime import UTC, datetime

import pytest
from skill_assessment.cli import main
from test_assessment_advice import gateway as gateway
from test_assessment_advice import scanner as scanner
from test_assessment_advice import skill as skill


@pytest.mark.parametrize("mode", ["llm-assisted", "static-only"])
def test_changed_skill_adds_assessment_and_preserves_history(skill, scanner, gateway, tmp_path, mode):
    output = tmp_path / "boe"
    scanner["report"]["metadata"]["llm_requested"] = mode == "llm-assisted"
    args = ["assess", "--skill", str(skill), "--output-dir", str(output),
            "--scan-mode", mode, "--timeout", "600"]
    started = datetime.now(UTC)
    history = []
    retained = {}

    for run in range(2):
        if run == 1:
            (skill / "references").mkdir()
            (skill / "references" / "usage.md").write_text("Additional guidance.\n")
        assert main(args) == 0
        index = json.loads((output / "index.json").read_text())
        assert index["boe_schema_version"] == 1
        assert index["skill"] == skill.name
        assert index["assessments"][1:] == history
        history = index["assessments"]
        entry = history[0]
        assert started <= datetime.fromisoformat(entry["assessed_at"]) <= datetime.now(UTC)
        assert len(entry["skill_sha256"]) == 64
        report_dir = output / entry["path"]
        assert report_dir.parent == output
        assert json.loads((report_dir / "skillspector.json").read_text()) == scanner["report"]
        adjudication = json.loads((report_dir / "adjudication.json").read_text())
        assert adjudication["status"] == ("completed" if mode == "llm-assisted" else "not_performed")
        assert (report_dir / "scanner.log").read_text() == "scanner diagnostics\n"
        assert all(path.read_bytes() == content for path, content in retained.items())
        retained.update({path: path.read_bytes() for path in report_dir.iterdir()})

    assert len({entry["path"] for entry in history}) == 2
    assert history[0]["skill_sha256"] != history[1]["skill_sha256"]
    assert scanner["timeouts"] == [600, 600]
    assert len(gateway["calls"]) == (2 if mode == "llm-assisted" else 0)


@pytest.mark.parametrize("mode", ["llm-assisted", "static-only"])
def test_duplicate_hash_rejected_without_scanning_or_changes(skill, scanner, tmp_path, capsys, mode):
    output = tmp_path / "boe"
    args = ["assess", "--skill", str(skill), "--output-dir", str(output)]
    assert main(args) == 0
    before = {path: path.read_bytes() for path in output.rglob("*") if path.is_file()}
    entry = json.loads((output / "index.json").read_text())["assessments"][0]
    calls = len(scanner["calls"])

    assert main([*args, "--scan-mode", mode]) == 1

    assert len(scanner["calls"]) == calls
    assert {path: path.read_bytes() for path in output.rglob("*") if path.is_file()} == before
    error = capsys.readouterr().err
    assert str(output / entry["path"]) in error
    assert "--override" in error


def test_override_replaces_hash_assessment_and_preserves_other_hashes(skill, scanner, tmp_path):
    output = tmp_path / "boe"
    args = ["assess", "--skill", str(skill), "--output-dir", str(output)]
    source = skill / "SKILL.md"
    original = source.read_text()
    assert main(args) == 0
    first = json.loads((output / "index.json").read_text())["assessments"][0]
    source.write_text(original + "Updated instructions.\n")
    assert main(args) == 0
    other = json.loads((output / "index.json").read_text())["assessments"][0]
    retained = {path: path.read_bytes() for path in (output / other["path"]).iterdir()}
    source.write_text(original)
    (output / first["path"] / "scanner.log").write_text("old diagnostics")
    scanner["report"]["metadata"]["llm_requested"] = False

    assert main([*args, "--override", "--scan-mode", "static-only"]) == 0

    index = json.loads((output / "index.json").read_text())
    latest = index["assessments"][0]
    assert latest["path"] == first["path"]
    assert latest["skill_sha256"] == first["skill_sha256"]
    assert latest["assessed_at"] > first["assessed_at"]
    assert index["assessments"][1:] == [other]
    assert set(latest) == {"assessed_at", "path", "skill_sha256", "reports"}
    assert {path.name for path in output.iterdir()} == {"index.json", first["path"], other["path"]}
    assert all(path.read_bytes() == content for path, content in retained.items())
    directory = output / latest["path"]
    assert json.loads((directory / "skillspector.json").read_text()) == scanner["report"]
    assert json.loads((directory / "adjudication.json").read_text())["status"] == "not_performed"
    assert (directory / "scanner.log").read_text() == "scanner diagnostics\n"


@pytest.mark.parametrize("failure", ["scanner", "timeout", "adjudication"])
@pytest.mark.parametrize("prior_assessment", [False, True])
def test_failed_assess_retains_diagnostics_without_updating_index(
    skill, scanner, gateway, tmp_path, capsys, failure, prior_assessment,
):
    output = tmp_path / "boe"
    args = ["assess", "--skill", str(skill), "--output-dir", str(output)]
    if prior_assessment:
        assert main(args) == 0
        args.append("--override")
    before = {path: path.read_bytes() for path in output.rglob("*") if path.is_file()}
    if failure == "scanner":
        scanner["status"] = 2
    elif failure == "timeout":
        scanner["error"] = subprocess.TimeoutExpired("skillspector", 300)
    else:
        gateway["error"] = TimeoutError("gateway unavailable")

    assert main(args) == 3

    assert all(path.read_bytes() == content for path, content in before.items())
    if not prior_assessment:
        assert not (output / "index.json").exists()
    logs = [path for path in output.glob("*/scanner.log") if path not in before]
    assert len(logs) == 1
    assert logs[0].read_text() == "scanner diagnostics\n"
    assert json.loads(logs[0].with_name("skillspector.json").read_text()) == scanner["report"]
    result = json.loads(logs[0].with_name("adjudication.json").read_text())
    assert result["status"] == ("failed" if failure == "adjudication" else "unavailable")
    assert str(logs[0].parent) in capsys.readouterr().err


def test_unreadable_history_preserves_index_without_scanning(skill, scanner, tmp_path, capsys):
    output = tmp_path / "boe"
    output.mkdir()
    index = output / "index.json"
    original = '{"boe_schema_version": 1, "skill": "my-skill", "assessments": null}\n'
    index.write_text(original)

    assert main(["assess", "--skill", str(skill), "--output-dir", str(output)]) == 1

    assert index.read_text() == original
    assert not scanner["calls"]
    assert list(output.iterdir()) == [index]
    assert capsys.readouterr().err
