import json
import subprocess
from pathlib import Path

import pytest
from skill_assessment.cli import main
from skill_assessment.commands.advise import advise_skill
from skill_assessment.errors import (
    IncompleteScanError,
    InvalidOutputDirectoryError,
    MissingFrontmatterError,
    ScanError,
)


@pytest.fixture
def skill(tmp_path):
    path = tmp_path / "my-skill"
    path.mkdir()
    (path / "SKILL.md").write_text("---\nname: my-skill\ndescription: Example\n---\nInstructions.\n")
    return path


@pytest.fixture
def scanner(monkeypatch):
    report = {
        "execution_successful": True,
        "analysis_completeness": {"is_complete": True},
        "metadata": {"llm_requested": True, "llm_available": True},
        "risk_assessment": {"score": 80, "severity": "HIGH"},
        "issues": [{"id": "CE1", "severity": "HIGH", "location": {"file": "run.py", "start_line": 3},
                    "explanation": "Untrusted input reaches eval", "remediation": "Parse data without eval"}],
    }
    state = {"report": report, "status": 1, "calls": []}

    def scan(command, *, stdout, **kwargs):
        state["calls"].append(command)
        stdout.write("scanner diagnostics\n")
        path = Path(command[command.index("--output") + 1])
        if state["report"] is not None:
            path.write_text(json.dumps(state["report"]), encoding="utf-8")
        if "error" in state:
            raise state["error"]
        return subprocess.CompletedProcess(command, state["status"])

    monkeypatch.setattr(subprocess, "run", scan)
    return state


def test_retains_useful_native_findings_across_runs(skill, scanner, tmp_path, monkeypatch):
    # Arrange
    monkeypatch.chdir(tmp_path)
    before = (skill / "SKILL.md").read_bytes()

    # Act
    codes = [main(["advise", "--skill", str(skill)]) for _ in range(2)]

    # Assert
    assert codes == [0, 0]  # Risk findings are advice, not execution failures.
    reports = list((tmp_path / "assessment-reports").glob("*/skillspector.json"))
    assert len(reports) == 2
    assert all(json.loads(path.read_text()) == scanner["report"] for path in reports)
    assert all(path.with_name("scanner.log").read_text() for path in reports)
    assert all("--no-llm" not in command for command in scanner["calls"])
    assert list(skill.iterdir()) == [skill / "SKILL.md"]
    assert (skill / "SKILL.md").read_bytes() == before


@pytest.mark.parametrize("failure", [
    "process", "missing", "malformed", "execution", "partial",
    "unavailable", "degraded", "lost-calls", "mode", "timeout",
])
def test_failed_scans_retain_artifacts_and_never_retry(skill, scanner, tmp_path, failure):
    # Arrange
    expected_error = IncompleteScanError
    report = scanner["report"]
    if failure in ("process", "missing", "malformed", "execution", "timeout"):
        expected_error = ScanError
    if failure == "process":
        scanner["status"] = 2
    elif failure == "missing":
        scanner["report"] = None
    elif failure == "malformed":
        scanner["report"] = ["unexpected report shape"]
    elif failure == "execution":
        report["execution_successful"] = False
    elif failure == "partial":
        report["analysis_completeness"]["is_complete"] = False
    elif failure == "unavailable":
        report["metadata"]["llm_available"] = False
    elif failure == "degraded":
        report["metadata"]["llm_degraded"] = True
    elif failure == "lost-calls":
        report["metadata"].update(llm_calls_attempted=2, llm_calls_succeeded=1)
    elif failure == "mode":
        report["metadata"]["llm_requested"] = False
    elif failure == "timeout":
        scanner["error"] = subprocess.TimeoutExpired("skillspector", 300)
    output = tmp_path / "retained"

    # Act
    with pytest.raises(expected_error) as error:
        advise_skill(skill, output)
    code = main(["advise", "--skill", str(skill), "--output-dir", str(output)])

    # Assert
    assert code == 3
    assert error.value.report_dir.parent == output
    assert len(scanner["calls"]) == 2  # One attempt per public invocation; no static retry.
    assert all("--no-llm" not in command for command in scanner["calls"])
    runs = list(output.iterdir())
    assert len(runs) == 2
    for run in runs:
        assert (run / "scanner.log").read_text()
        path = run / "skillspector.json"
        if scanner["report"] is None:
            assert not path.exists()
        else:
            assert json.loads(path.read_text()) == scanner["report"]


@pytest.mark.parametrize("invalid_skill", [False, True])
def test_rejects_invalid_input_before_writing_or_scanning(skill, scanner, invalid_skill):
    # Arrange
    expected_error = InvalidOutputDirectoryError
    if invalid_skill:
        (skill / "SKILL.md").write_text("No frontmatter")
        expected_error = MissingFrontmatterError
    before = (skill / "SKILL.md").read_bytes()
    output = skill / "reports"

    # Act
    with pytest.raises(expected_error):
        advise_skill(skill, output)
    code = main(["advise", "--skill", str(skill), "--output-dir", str(output)])

    # Assert
    assert code == 1
    assert not scanner["calls"]
    assert not output.exists()
    assert (skill / "SKILL.md").read_bytes() == before


def test_rejects_multiple_skills_before_scanning(skill, scanner):
    # Arrange
    args = ["advise", "--skill", str(skill), "--skill", str(skill)]

    # Act
    with pytest.raises(SystemExit) as error:
        main(args)

    # Assert
    assert error.value.code == 2
    assert not scanner["calls"]


def test_real_static_scan_provides_actionable_findings(skill, tmp_path):
    # Arrange
    script = skill / "run.py"
    script.write_text("eval(input('Expression: '))\n")
    before = {path.name: path.read_bytes() for path in skill.iterdir()}
    output = tmp_path / "reports"

    # Act
    code = main(["advise", "--skill", str(skill), "--scan-mode", "static-only", "--output-dir", str(output)])

    # Assert
    assert code == 0
    report = json.loads(next(output.glob("*/skillspector.json")).read_text())
    assert report["metadata"]["llm_requested"] is False
    findings = [issue for issue in report["issues"] if issue["location"]["file"].endswith("run.py")]
    assert findings
    assert all(issue["explanation"] and issue["remediation"] for issue in findings)
    assert {path.name: path.read_bytes() for path in skill.iterdir()} == before
