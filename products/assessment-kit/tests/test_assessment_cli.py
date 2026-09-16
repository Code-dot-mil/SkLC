import hashlib
import json
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator

from skill_assessment import cli
from skill_assessment.cli import main
from skill_assessment.errors import AssessmentError, RetryableAssessmentError
from skill_assessment.skillspector import NativeReport


def test_validate_command_writes_no_files(skill, capsys):
    before = list(skill.parent.rglob("*"))
    assert main(["validate", "--skill", str(skill)]) == 0
    assert "valid example-skill sha256:" in capsys.readouterr().out
    assert list(skill.parent.rglob("*")) == before


def test_assess_retains_exact_report_idempotently_and_verifies_tampering(skill, scanner, report, tmp_path):
    scanner()
    root = tmp_path / "boe"
    args = ["assess", "--skill", str(skill), "--assessor", "skillspector", "--boe-root", str(root)]
    assert main(args) == 0
    directory = root / skill.name
    manifest = (directory / "boe.json").read_bytes()
    raw = json.dumps(report).encode()
    digest = hashlib.sha256(raw).hexdigest()
    relative = f"assessments/skillspector/{digest}.json"
    assert (directory / relative).read_bytes() == raw
    assert json.loads(manifest)["assessments"] == [{"path": relative, "sha256": f"sha256:{digest}"}]
    assert main(args) == 0
    assert (directory / "boe.json").read_bytes() == manifest
    verify = ["verify-boe", "--skill", str(skill), str(directory)]
    assert main(verify) == 0
    (directory / relative).write_text("{}")
    assert main(verify) == 2


def test_advice_preserves_findings_and_native_bytes_without_boe(skill, scanner, report, tmp_path):
    report["issues"] = [
        {"severity": "high", "category": "prompt-injection", "location": "SKILL.md:10",
         "finding": "Unsafe instruction", "pattern": "ignore prior", "confidence": "high",
         "explanation": "Overrides policy", "remediation": "Remove it",
         "occurrences": [{"file": "a.py", "start_line": 3}]},
        {"severity": "high", "explanation": "Second distinct issue", "code_snippet": "unsafe()"},
    ]
    scanner(exit_code=0)
    output = tmp_path / "advice"
    assert main(["advise", "--skill", str(skill), "--assessor", "skillspector", "--output", str(output)]) == 0
    manifest = json.loads((output / "advice-manifest.json").read_text())
    schema = Path(__file__).parents[3] / "contracts/assessment-artifacts/v1/advice-manifest.schema.json"
    Draft202012Validator(json.loads(schema.read_text())).validate(manifest)
    advice = (output / "advice.md").read_bytes()
    assert manifest["skills"] == [skill.name]
    assert manifest["assessors"] == ["skillspector"]
    assert manifest["advice_sha256"] == "sha256:" + hashlib.sha256(advice).hexdigest()
    for finding in report["issues"]:
        for field, value in finding.items():
            assert field in advice.decode()
            assert (value if isinstance(value, str) else json.dumps(value, sort_keys=True)) in advice.decode()
    assert not list(output.rglob("boe.json"))
    entry, = manifest["native_reports"]
    raw = (output / entry["path"]).read_bytes()
    assert raw == json.dumps(report).encode()
    assert entry["sha256"] == "sha256:" + hashlib.sha256(raw).hexdigest()


@pytest.mark.parametrize("invalid", ["package", "llm-config", "output-overlap"])
def test_invalid_inputs_fail_before_execution(skill, tmp_path, monkeypatch, capsys, invalid):
    def unexpected_call():
        pytest.fail("invalid input reached assessor execution")
    monkeypatch.setattr(cli, "resolve_binary", unexpected_call)
    output = tmp_path / "output"
    if invalid == "llm-config":
        message = "SKLC_LLM_API_KEY"
    else:
        monkeypatch.setenv("SKLC_SKILLSPECTOR_SCAN_MODE", "static-only")
        if invalid == "package":
            (skill / "SKILL.md").write_text("not frontmatter")
            message = "frontmatter"
        else:
            output = skill / "generated"
            message = "inside skill package"
    assert main(["assess", "--skill", str(skill), "--assessor", "skillspector", "--boe-root", str(output)]) == 2
    assert message in capsys.readouterr().err
    assert not output.exists()


@pytest.mark.parametrize("command,flag", [("advise", "--output"), ("assess", "--boe-root")])
def test_empty_selection_needs_no_assessor_but_validates_config(tmp_path, monkeypatch, command, flag):
    def unexpected_call():
        pytest.fail("empty selection reached assessor execution")
    monkeypatch.setattr(cli, "resolve_binary", unexpected_call)
    empty, output = tmp_path / "empty", tmp_path / "output"
    args = [command, "--root", str(empty), "--assessor", "skillspector", flag, str(output)]
    assert main(args) == 2
    empty.mkdir()
    assert main(args) == 0
    config = tmp_path / "config.json"
    config.write_text(json.dumps({"assessors": {"unknown": {}}}))
    assert main([*args, "--config", str(config)]) == 2
    assert not output.exists()


@pytest.mark.parametrize("command,flag,write_failure", [
    ("assess", "--boe-root", False), ("advise", "--output", False), ("advise", "--output", True),
])
def test_batch_retains_success_and_retryable_exit(
    monkeypatch, tmp_path, make_skill, report, capsys, command, flag, write_failure,
):
    skills = tmp_path / "skills"
    for name in ("good", "temporary", "broken"):
        make_skill(skills, name)
    calls = []

    def assess(path, *args, **kwargs):
        calls.append(path.name)
        if path.name == "temporary":
            raise RetryableAssessmentError("temporary failure")
        if path.name == "broken":
            raise AssessmentError("permanent failure")
        return NativeReport(json.dumps(report).encode(), report)

    monkeypatch.setattr(cli, "resolve_binary", lambda: "skillspector")
    monkeypatch.setattr(cli, "require_supported_version", lambda binary: None)
    monkeypatch.setattr(cli, "run", assess)
    monkeypatch.setenv("SKLC_SKILLSPECTOR_SCAN_MODE", "static-only")
    output = tmp_path / "output"
    if write_failure:
        (output / "advice.md").mkdir(parents=True)
    assert main([command, "--root", str(skills), "--assessor", "skillspector", flag, str(output)]) == 10
    assert sorted(calls) == ["broken", "good", "temporary"]
    diagnostic = capsys.readouterr().err
    assert "temporary failure" in diagnostic and "permanent failure" in diagnostic
    if command == "assess":
        assert [p.name for p in output.iterdir()] == ["good"]
        assert main(["verify-boe", "--skill", str(skills / "good"), str(output / "good")]) == 0
    elif write_failure:
        assert "cannot write" in diagnostic
        assert not (output / "advice-manifest.json").exists()
    else:
        entries = json.loads((output / "advice-manifest.json").read_text())["native_reports"]
        assert [entry["skill_name"] for entry in entries] == ["good"]


def test_unresolvable_output_is_a_diagnostic_error(skill, tmp_path, monkeypatch, capsys):
    loop = tmp_path / "loop"
    loop.symlink_to(loop)
    monkeypatch.setenv("SKLC_SKILLSPECTOR_SCAN_MODE", "static-only")
    assert main(["advise", "--skill", str(skill), "--assessor", "skillspector", "--output", str(loop)]) == 2
    assert "cannot resolve command output" in capsys.readouterr().err
