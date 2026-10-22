import json
import subprocess
import urllib.request

import pytest
from skill_assessment.adjudication import SCOPE, not_adjudicated
from skill_assessment.cli import main


@pytest.fixture
def assessment(tmp_path, monkeypatch):
    def unexpected_call(*args, **kwargs):
        pytest.fail("Summary unexpectedly invoked a scanner or provider")

    monkeypatch.setattr(subprocess, "run", unexpected_call)
    monkeypatch.setattr(urllib.request.OpenerDirector, "open", unexpected_call)
    issues = [
        {"id": "CE1", "pattern": "Code execution", "category": "Execution",
         "location": {"file": "run.py", "start_line": 3}, "finding": "eval(input)",
         "explanation": "Input executes as code", "remediation": "Parse data without eval"},
        {"id": "AR3", "pattern": "Anti-refusal", "category": "Anti-Refusal",
         "location": {"file": "SKILL.md", "start_line": 12}, "explanation": "Bypass filters"},
        {"id": "NET1", "pattern": "Network access", "category": "Network",
         "location": {"file": "send.py", "start_line": 5}, "explanation": "Unknown destination"},
    ]
    verdict = {
        "status": "completed", "safe_to_use": False, "summary": "Review required.",
        "coverage_sufficient": True, "coverage_reason": "All supplied context reviewed.", "scope": SCOPE,
        "metadata": {"created_at": "2026-10-20T12:00:00+00:00"},
        "findings": [
            {"index": index, "rule_id": issue["id"], "determination": determination, "reason": reason}
            for index, (issue, determination, reason) in enumerate(zip(issues,
                ["true_positive", "false_positive", "uncertain"],
                ["Executes user input", "Inert example", "Destination needs review"], strict=True), 1)
        ],
    }

    def save():
        (tmp_path / "skillspector.json").write_text(json.dumps({
            "issues": issues, "execution_successful": True, "analysis_completeness": {"is_complete": True},
            "metadata": {"llm_requested": True, "llm_available": True,
                         "llm_calls_attempted": 1, "llm_calls_succeeded": 1},
        }))
        (tmp_path / "adjudication.json").write_text(json.dumps(verdict))

    save()
    return tmp_path, issues, verdict, save


def test_mixed_summary_explains_actions_and_preserves_evidence(assessment, capsys):
    directory, _, _, _ = assessment
    before = {path: path.read_bytes() for path in directory.iterdir()}
    assert main(["summarize", "--assessment-dir", str(directory)]) == 0
    output = capsys.readouterr().out
    assert "1 confirmed finding requires remediation" in output
    assert "| Unresolved findings | 1 |" in output and "| False positives | 1 |" in output
    assert "run\\.py:3" in output and "send\\.py:5" in output
    assert "Parse data without eval" in output and "Destination needs review" in output
    compact = output.split("## False positives")[1]
    assert "Inert example" in compact and "SKILL\\.md:12" in compact
    assert "Bypass filters" not in compact
    assert "Scope:" in output and "All supplied context reviewed" in output
    assert {path: path.read_bytes() for path in directory.iterdir()} == before


def test_false_positive_only_summary_does_not_invent_remediation(assessment, capsys):
    directory, _, verdict, save = assessment
    for finding in verdict["findings"]:
        finding.update(determination="false_positive", reason="Inert example")
    verdict["safe_to_use"] = True
    save()
    assert main(["summarize", "--assessment-dir", str(directory)]) == 0
    output = capsys.readouterr().out
    assert "0 confirmed findings require remediation" in output
    assert "| Unresolved findings | 0 |" in output and "| False positives | 3 |" in output
    assert "Requires remediation" not in output and "Remediation:" not in output
    assert "Safety is not established" not in output


@pytest.mark.parametrize("complete", [True, False, None])
def test_native_coverage_is_reported_alongside_bounded_adjudication(assessment, capsys, complete):
    directory, _, verdict, save = assessment
    for finding in verdict["findings"]:
        finding["determination"] = "false_positive"
    verdict["safe_to_use"] = True
    verdict["coverage_reason"] = "Supplied context sufficient despite optional missing references."
    save()
    path = directory / "skillspector.json"
    report = json.loads(path.read_text())
    report["analysis_completeness"] = {"is_complete": complete}
    path.write_text(json.dumps(report))
    assert main(["summarize", "--assessment-dir", str(directory)]) == 0
    output = capsys.readouterr().out
    expected = "complete" if complete is True else "partial" if complete is False else "not reported"
    assert f"| Scanner-reported coverage | {expected} |" in output
    assert "Supplied context sufficient despite optional missing references" in output
    assert "Safety is not established" not in output


def test_insufficient_context_remains_visible_even_without_true_positives(assessment, capsys):
    directory, _, verdict, save = assessment
    for finding in verdict["findings"]:
        finding["determination"] = "false_positive"
    verdict.update(coverage_sufficient=False, coverage_reason="Required file content was unavailable.")
    save()
    assert main(["summarize", "--assessment-dir", str(directory)]) == 0
    output = capsys.readouterr().out
    assert "Required file content was unavailable" in output
    assert "Safety is not established" in output


@pytest.mark.parametrize("failure", ["llm_degraded", "execution"])
def test_retained_native_failures_remain_visible_with_completed_adjudication(assessment, capsys, failure):
    directory, _, verdict, save = assessment
    for finding in verdict["findings"]:
        finding["determination"] = "false_positive"
    verdict["safe_to_use"] = True
    save()
    path = directory / "skillspector.json"
    report = json.loads(path.read_text())
    if failure == "execution":
        report["execution_successful"] = False
    else:
        report["metadata"]["llm_degraded"] = True
    path.write_text(json.dumps(report))
    assert main(["summarize", "--assessment-dir", str(directory)]) == 0
    output = capsys.readouterr().out
    assert "Scanner execution failed or requested analysis was unavailable or degraded" in output
    assert "degraded" in output and "Safety is not established" in output
    assert "False positives" in output  # Existing determinations remain available for human review.


@pytest.mark.parametrize("status", ["not_performed", "unavailable", "failed"])
def test_unadjudicated_reports_keep_findings_unresolved(assessment, capsys, status):
    directory, issues, verdict, save = assessment
    verdict.update(not_adjudicated(issues, "Review did not run."), status=status)
    save()
    assert main(["summarize", "--assessment-dir", str(directory)]) == 0
    output = capsys.readouterr().out
    assert "0 confirmed findings require remediation" in output
    assert "| Unresolved findings | 3 |" in output and "| False positives | 0 |" in output
    assert status.replace("_", "\\_") in output
    assert "Safety is not established" in output and "| Coverage judgment | not assessed |" in output
    assert "Unknown destination" in output and "Review did not run" in output


@pytest.mark.parametrize("mismatch", ["index", "rule_id", "missing", "contradiction"])
def test_mismatched_reports_fail_without_partial_markdown(assessment, capsys, mismatch):
    directory, _, verdict, save = assessment
    if mismatch == "missing":
        verdict["findings"].pop()
    elif mismatch == "contradiction":
        verdict["safe_to_use"] = True
    else:
        verdict["findings"][0][mismatch] = 2 if mismatch == "index" else "OTHER"
    save()
    assert main(["summarize", "--assessment-dir", str(directory)]) == 1
    captured = capsys.readouterr()
    assert not captured.out and captured.err


def test_report_text_cannot_inject_markdown_or_html(assessment, capsys):
    directory, issues, verdict, save = assessment
    issues[0]["pattern"] = "<script>alert(1)</script>\n## injected"
    verdict["findings"][0]["reason"] = "[click](https://example.invalid) ![image](x) `code` &lt;b&gt;"
    save()
    assert main(["summarize", "--assessment-dir", str(directory)]) == 0
    output = capsys.readouterr().out
    assert "<script>" not in output and "\n## injected" not in output
    assert "[click](" not in output and "![image](" not in output
    assert "\\<script\\>" in output and "\\&lt;b" in output


@pytest.mark.parametrize("content", [None, "invalid json", "[]"])
def test_unreadable_report_pair_returns_error_without_summary(assessment, capsys, content):
    directory, _, _, _ = assessment
    path = directory / "adjudication.json"
    if content is None:
        path.unlink()
    else:
        path.write_text(content)
    assert main(["summarize", "--assessment-dir", str(directory)]) == 1
    captured = capsys.readouterr()
    assert not captured.out and captured.err
