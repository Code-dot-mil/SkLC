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
