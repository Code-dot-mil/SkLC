import json
import subprocess
from datetime import UTC, datetime

import pytest
from skill_assessment.cli import main


@pytest.mark.parametrize("mode", ["llm-assisted", "static-only"])
def test_success_replaces_only_current_reports_and_rescans_by_default(skill, scanner, gateway, tmp_path, mode):
    output = tmp_path / "reports"
    output.mkdir()
    note = output / "notes.txt"
    note.write_text("Retain this customer file.")
    scanner["report"]["metadata"]["llm_requested"] = mode == "llm-assisted"
    args = ["assess", "--skill", str(skill), "--output-dir", str(output),
            "--scan-mode", mode, "--timeout", "600"]
    started = datetime.now(UTC)
    for _ in range(2):
        assert main(args) == 0
        assert json.loads((output / "skillspector.json").read_text()) == scanner["report"]
        adjudication = json.loads((output / "adjudication.json").read_text())
        assert started <= datetime.fromisoformat(adjudication["metadata"]["created_at"]) <= datetime.now(UTC)
        assert len(adjudication["skill_sha256"]) == 64
        assert adjudication["status"] == ("completed" if mode == "llm-assisted" else "not_performed")
        assert (output / "scanner.log").read_text() == "scanner diagnostics\n"
    assert {path.name for path in output.iterdir()} == {
        "skillspector.json", "adjudication.json", "scanner.log", "notes.txt",
    }
    assert note.read_text() == "Retain this customer file."
    assert not list(tmp_path.glob("my-skill-*"))
    assert scanner["timeouts"] == [600, 600]
    assert len(gateway["calls"]) == (2 if mode == "llm-assisted" else 0)


@pytest.mark.parametrize("mode", ["llm-assisted", "static-only"])
def test_if_changed_skips_only_matching_successful_reports(skill, scanner, tmp_path, mode):
    output = tmp_path / "reports"
    scanner["report"]["metadata"]["llm_requested"] = mode == "llm-assisted"
    args = ["assess", "--skill", str(skill), "--output-dir", str(output), "--scan-mode", mode, "--if-changed"]
    assert main(args) == 0
    (output / "scanner.log").unlink()  # Diagnostic output is not required evidence.
    before = {path: path.read_bytes() for path in output.iterdir()}
    assert main(args) == 0
    assert len(scanner["calls"]) == 1
    assert before == {path: path.read_bytes() for path in output.iterdir()}
    (skill / "support.md").write_text("Changed supporting file")
    assert main(args) == 0
    assert len(scanner["calls"]) == 2
    assert json.loads((output / "adjudication.json").read_text())["skill_sha256"] != json.loads(
        before[output / "adjudication.json"]
    )["skill_sha256"]


@pytest.mark.parametrize("invalid", [
    "mode", "failed", "adjudication", "malformed",
    "fields-only", "missing-metadata", "missing-finding", "mismatched-finding",
])
@pytest.mark.parametrize("mode", ["llm-assisted", "static-only"])
def test_if_changed_rescans_unusable_reports(skill, scanner, tmp_path, invalid, mode):
    output = tmp_path / "reports"
    scanner["report"]["metadata"]["llm_requested"] = mode == "llm-assisted"
    args = ["assess", "--skill", str(skill), "--output-dir", str(output), "--if-changed", "--scan-mode", mode]
    assert main(args) == 0
    path = output / "skillspector.json"
    report = json.loads(path.read_text())
    if invalid == "mode":
        report["metadata"]["llm_requested"] = mode != "llm-assisted"
    elif invalid == "failed":
        report["execution_successful"] = False
    elif invalid == "adjudication":
        path = output / "adjudication.json"
        report = json.loads(path.read_text())
        report["status"] = "failed"
    elif invalid in {"fields-only", "missing-metadata", "missing-finding", "mismatched-finding"}:
        path = output / "adjudication.json"
        report = json.loads(path.read_text())
        if invalid == "fields-only":
            report = {key: report[key] for key in ("skill_sha256", "status")}
        elif invalid == "missing-metadata":
            del report["metadata"]
        elif invalid == "missing-finding":
            report["findings"] = []
        else:
            report["findings"][0]["rule_id"] = "wrong-native-issue"
    path.write_text("invalid json" if invalid == "malformed" else json.dumps(report))
    assert main(args) == 0
    assert len(scanner["calls"]) == 2


@pytest.mark.parametrize("failure", ["scanner", "timeout", "adjudication"])
@pytest.mark.parametrize("prior_assessment", [False, True])
def test_failed_assess_retains_diagnostics_outside_unchanged_current_reports(
    skill, scanner, gateway, tmp_path, capsys, failure, prior_assessment,
):
    output = tmp_path / "boe"
    args = ["assess", "--skill", str(skill), "--output-dir", str(output)]
    if prior_assessment:
        assert main(args) == 0
    before = {path: path.read_bytes() for path in output.rglob("*") if path.is_file()}
    if failure == "scanner":
        scanner["status"] = 2
    elif failure == "timeout":
        scanner["error"] = subprocess.TimeoutExpired("skillspector", 300)
    else:
        gateway["error"] = TimeoutError("gateway unavailable")

    assert main(args) == 3

    assert before == {path: path.read_bytes() for path in output.rglob("*") if path.is_file()}
    if not prior_assessment:
        assert not output.exists()
    logs = list(tmp_path.glob("my-skill-*/scanner.log"))
    assert len(logs) == 1
    assert logs[0].read_text() == "scanner diagnostics\n"
    assert json.loads(logs[0].with_name("skillspector.json").read_text()) == scanner["report"]
    result = json.loads(logs[0].with_name("adjudication.json").read_text())
    assert result["status"] == ("failed" if failure == "adjudication" else "unavailable")
    assert str(logs[0].parent) in capsys.readouterr().err


@pytest.mark.parametrize("invalid", ["inside-skill", "metadata"])
def test_invalid_assessment_input_does_not_scan(skill, scanner, tmp_path, capsys, invalid):
    output = skill / "reports" if invalid == "inside-skill" else tmp_path / "reports"
    if invalid == "metadata":
        (skill / "SKILL.md").write_text("Missing frontmatter")
    assert main(["assess", "--skill", str(skill), "--output-dir", str(output)]) == 1
    assert not scanner["calls"]
    assert not output.exists()
    assert capsys.readouterr().err


@pytest.mark.parametrize("if_changed", [False, True])
def test_missing_scanner_preserves_existing_reports_without_new_artifacts(
    skill, scanner, tmp_path, monkeypatch, capsys, if_changed,
):
    output = tmp_path / "reports"
    args = ["assess", "--skill", str(skill), "--output-dir", str(output)]
    assert main(args) == 0
    capsys.readouterr()
    before = {path: path.read_bytes() if path.is_file() else None for path in tmp_path.rglob("*")}
    monkeypatch.setattr("shutil.which", lambda command: None)

    assert main([*args, *(["--if-changed"] if if_changed else []), "--base-dir", str(tmp_path)]) == 3

    assert {path: path.read_bytes() if path.is_file() else None for path in tmp_path.rglob("*")} == before
    assert not capsys.readouterr().out
    assert len(scanner["calls"]) == 1
