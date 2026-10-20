import json
import subprocess
import urllib.request

import pytest
from skill_assessment.cli import main


@pytest.mark.parametrize("mode", ["llm-assisted", "static-only"])
def test_base_dir_strips_only_source_before_adjudication(skill, scanner, gateway, tmp_path, monkeypatch, mode):
    scanner["report"].update(skill={"source": str(skill), "name": "my-skill"}, other_path=str(skill))
    scanner["report"]["metadata"]["llm_requested"] = mode == "llm-assisted"
    scanner["report"]["issues"][0]["location"]["file"] = str(skill / "run.py")
    expected = json.loads(json.dumps(scanner["report"]))
    expected["skill"]["source"] = "my-skill"
    original_open = urllib.request.OpenerDirector.open

    def adjudicate(opener, request, **kwargs):
        # Observe staged evidence at the external provider boundary.
        staged = next(tmp_path.glob("my-skill-*/skillspector.json"))
        assert json.loads(staged.read_text()) == expected
        return original_open(opener, request, **kwargs)

    monkeypatch.setattr(urllib.request.OpenerDirector, "open", adjudicate)
    monkeypatch.chdir(tmp_path)
    output = tmp_path / "current"
    args = ["assess", "--skill", str(skill), "--output-dir", str(output), "--scan-mode", mode]

    assert main([*args, "--base-dir", "./"]) == 0
    assert json.loads((output / "skillspector.json").read_text()) == expected
    assert len(gateway["calls"]) == (1 if mode == "llm-assisted" else 0)


@pytest.mark.parametrize("source", ["sibling", "traversal", "relative", "url", "missing", None, 42])
def test_base_dir_preserves_unmatched_source_bytes(skill, scanner, tmp_path, source):
    sources = {"sibling": str(skill) + "-other", "traversal": str(skill / ".." / "elsewhere"),
               "relative": "my-skill", "url": "https://example.test/skills/my-skill"}
    scanner["report"]["skill"] = {} if source == "missing" else {"source": sources.get(source, source)}
    scanner["native"] = json.dumps(scanner["report"], indent=3) + "  \n"
    output = tmp_path / "current"

    assert main(["assess", "--skill", str(skill), "--output-dir", str(output), "--base-dir", str(skill)]) == 0
    assert (output / "skillspector.json").read_text() == scanner["native"]


def test_without_base_dir_preserves_native_bytes(skill, scanner, tmp_path):
    scanner["report"]["skill"] = {"source": str(skill)}
    scanner["native"] = json.dumps(scanner["report"], indent=3) + "  \n"
    output = tmp_path / "current"

    assert main(["assess", "--skill", str(skill), "--output-dir", str(output)]) == 0
    assert (output / "skillspector.json").read_bytes() == scanner["native"].encode()


@pytest.mark.parametrize("failure", ["exit", "timeout", "malformed-timeout"])
def test_failed_scanner_retains_rebased_source_and_existing_reports(skill, scanner, tmp_path, capsys, failure):
    output = tmp_path / "current"
    args = ["assess", "--skill", str(skill), "--output-dir", str(output)]
    assert main(args) == 0
    before = {path: path.read_bytes() for path in output.iterdir()}
    scanner["report"]["skill"] = {"source": str(skill)}
    scanner["status"] = 2
    if failure != "exit":
        scanner["error"] = subprocess.TimeoutExpired("skillspector", 300)
    if failure == "malformed-timeout":
        scanner["native"] = "{unfinished"

    assert main([*args, "--base-dir", str(tmp_path) + "/"]) == 3
    failed = next(tmp_path.glob("my-skill-*/skillspector.json"))
    if failure == "malformed-timeout":
        assert failed.read_text() == "{unfinished"
        assert "timed out" in capsys.readouterr().err
    else:
        assert json.loads(failed.read_text())["skill"]["source"] == "my-skill"
    assert json.loads(failed.with_name("adjudication.json").read_text())["status"] == "unavailable"
    assert failed.with_name("scanner.log").read_text()
    assert before == {path: path.read_bytes() for path in output.iterdir()}


def test_if_changed_can_strip_cached_source_without_scanning(skill, scanner, gateway, tmp_path):
    scanner["report"]["skill"] = {"source": str(skill)}
    output = tmp_path / "current"
    args = ["assess", "--skill", str(skill), "--output-dir", str(output), "--if-changed"]
    assert main(args) == 0
    before = (output / "adjudication.json").read_bytes()

    assert main([*args, "--base-dir", str(tmp_path)]) == 0
    assert json.loads((output / "skillspector.json").read_text())["skill"]["source"] == "my-skill"
    source_bytes = (output / "skillspector.json").read_bytes()
    assert main([*args, "--base-dir", str(tmp_path.parent)]) == 0
    assert (output / "skillspector.json").read_bytes() == source_bytes
    assert (output / "adjudication.json").read_bytes() == before
    assert len(scanner["calls"]) == len(gateway["calls"]) == 1


def test_base_dir_environment_can_be_overridden(skill, scanner, tmp_path, monkeypatch):
    scanner["report"]["skill"] = {"source": str(skill)}
    monkeypatch.setenv("SKILL_ASSESSMENT_BASE_DIR", str(tmp_path.parent))
    output = tmp_path / "current"
    args = ["assess", "--skill", str(skill), "--output-dir", str(output)]
    assert main(args) == 0
    expected = str(skill.relative_to(tmp_path.parent))
    assert json.loads((output / "skillspector.json").read_text())["skill"]["source"] == expected
    assert main([*args, "--base-dir", str(tmp_path)]) == 0
    assert json.loads((output / "skillspector.json").read_text())["skill"]["source"] == "my-skill"
