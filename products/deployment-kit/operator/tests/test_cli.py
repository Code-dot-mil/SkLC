import json
import shutil
import subprocess
import sys

import pytest
from skill_assessment.commands.summarize import summarize
from skill_exchange.cli import main


@pytest.mark.parametrize("force", [False, True])
def test_assessment_then_generation_uses_included_report_pair(current_assessment, tmp_path, monkeypatch, force):
    skills, source, *_ = current_assessment
    evidence = tmp_path / "evidence"
    calls = []
    run_process = subprocess.run

    def assessment_cli(command, **kwargs):
        calls.append(command)
        if command[1] == "assess":
            assert ("--if-changed" in command) is not force
            assert command[command.index("--skill") + 1] == str(skills / "sample-skill")
            output = command[command.index("--output-dir") + 1]
            assert output == str(evidence / "sample-skill")
            shutil.copytree(source, output, dirs_exist_ok=True)
        else:
            kwargs["stdout"].write(summarize(evidence / "sample-skill"))
        return subprocess.CompletedProcess(command, 0)

    monkeypatch.setattr(subprocess, "run", assessment_cli)
    arguments = ["catalog", "assess-catalog", "--skills", str(skills), "--evidence", str(evidence)]
    if force:
        arguments.append("--force")
    monkeypatch.setattr("sys.argv", arguments)
    main()
    assert "Requires remediation" in (evidence / "sample-skill/assessment.md").read_text()
    assert len([command for command in calls if command[1] == "assess"]) == 1
    before = {path: path.read_bytes() for path in evidence.rglob("*") if path.is_file()}

    def no_process(command, **kwargs):
        if command[0] == "git":
            return run_process(command, **kwargs)
        pytest.fail("Generating a catalog must not execute any assessment or scanner process")

    monkeypatch.setattr(subprocess, "run", no_process)
    generated = tmp_path / "generated"
    monkeypatch.setattr("sys.argv", ["catalog", "generate", "--skills", str(skills),
                                    "--evidence", str(evidence), "--generated", str(generated)])
    main()
    record = json.loads((generated / "index.json").read_text())["skills"][0]
    assert record["skill_id"] == "sample-skill"
    assert record["adjudication"]["summary"] == current_assessment[3]["summary"]
    assert before == {path: path.read_bytes() for path in evidence.rglob("*") if path.is_file()}


def test_generate_uses_selected_evidence_and_output(current_assessment, tmp_path, monkeypatch, capsys):
    skills, evidence, *_ = current_assessment
    subprocess.run(["git", "init", "-q", str(tmp_path)], check=True)
    subprocess.run(["git", "-C", str(tmp_path), "-c", "user.name=Fixture", "-c", "user.email=fixture@example.invalid",
                    "commit", "--allow-empty", "-qm", "Installed Operator"], check=True, capture_output=True)
    (tmp_path / "VERSION").write_text("1.2.0\n")
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(sys, "argv", ["catalog", "generate", "--skills", str(skills),
                                     "--generated", "preview", "--evidence", str(evidence.parent)])
    main()
    assert json.loads(capsys.readouterr().out)["skills_written"] == 1
    record = json.loads((tmp_path / "preview/index.json").read_text())["skills"][0]
    assert record["skill_id"] == "sample-skill"
    assert (tmp_path / "preview/zips/sample-skill.zip").is_file()
