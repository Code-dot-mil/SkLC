import json

import pytest
from skill_assessment.cli import main


@pytest.fixture
def partial_report(scanner):
    scanner["report"]["analysis_completeness"] = {
        "is_complete": False,
        "limitations": ["Some references could not be inspected."],
    }
    return scanner["report"]


@pytest.mark.parametrize("mode", ["llm-assisted", "static-only"])
def test_partial_assessment_retains_native_warnings_and_can_be_reused(
    skill, scanner, gateway, partial_report, tmp_path, capsys, mode,
):
    partial_report["metadata"]["llm_requested"] = mode == "llm-assisted"
    gateway["overrides"] = {"safe_to_use": False, "coverage_sufficient": False}
    output = tmp_path / "reports"
    args = ["assess", "--skill", str(skill), "--output-dir", str(output), "--scan-mode", mode]
    assert main(args) == 0
    assert json.loads((output / "skillspector.json").read_text()) == partial_report
    verdict = json.loads((output / "adjudication.json").read_text())
    assert verdict["safe_to_use"] is (False if mode == "llm-assisted" else None)
    before = {path: path.read_bytes() for path in output.iterdir()}
    assert main([*args, "--if-changed"]) == 0
    assert len(scanner["calls"]) == 1
    assert before == {path: path.read_bytes() for path in output.iterdir()}


def test_developer_addresses_confirmed_finding_and_checks_revised_skill(skill, scanner, gateway, tmp_path, capsys):
    skill_file = skill / "SKILL.md"
    skill_file.write_text(skill_file.read_text() + "Evaluate untrusted input with eval.\n")
    gateway["overrides"] = {
        "safe_to_use": False,
        "findings": [{"index": 1, "rule_id": "CE1", "determination": "true_positive", "reason": "Unsafe eval."}],
    }
    output = tmp_path / "reports"
    args = ["assess", "--skill", str(skill), "--output-dir", str(output)]
    assert main(args) == 0
    original_hash = json.loads((output / "adjudication.json").read_text())["skill_sha256"]
    capsys.readouterr()
    assert main(["summarize", "--assessment-dir", str(output)]) == 0
    assert "Parse data without eval" in capsys.readouterr().out

    skill_file.write_text(skill_file.read_text().replace("Evaluate untrusted input with eval.", "Parse input as data."))
    scanner["report"]["issues"] = []
    gateway["overrides"] = {}
    assert main([*args, "--if-changed"]) == 0
    revised = json.loads((output / "adjudication.json").read_text())
    assert revised["skill_sha256"] != original_hash
    capsys.readouterr()
    assert main(["summarize", "--assessment-dir", str(output)]) == 0
    summary = capsys.readouterr().out
    assert "0 confirmed findings require remediation" in summary
    assert "Parse data without eval" not in summary


@pytest.mark.parametrize("findings", [False, True])
def test_safe_single_file_assessment_can_be_reused_despite_coverage_warnings(
    skill, scanner, gateway, partial_report, tmp_path, findings,
):
    if not findings:
        partial_report["issues"] = []
    gateway["overrides"] = {"coverage_sufficient": False}
    output = tmp_path / "reports"
    args = ["assess", "--skill", str(skill), "--output-dir", str(output)]
    assert main(args) == 0
    verdict = json.loads((output / "adjudication.json").read_text())
    assert verdict["status"] == "completed"
    assert verdict["safe_to_use"] is True
    assert verdict["coverage_sufficient"] is False
    assert json.loads((output / "skillspector.json").read_text()) == partial_report
    assert main([*args, "--if-changed"]) == 0
    assert len(scanner["calls"]) == 1
