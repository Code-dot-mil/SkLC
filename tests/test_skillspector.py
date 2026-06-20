import json
import subprocess
from pathlib import Path

import pytest
from skill_exchange import skillspector


def test_run_skillspector_accepts_finding_exit_code_with_valid_report(monkeypatch, tmp_path: Path):
    report = {
        "risk_assessment": {"score": 100, "severity": "CRITICAL", "recommendation": "DO_NOT_INSTALL"},
        "issues": [{"id": "E2", "severity": "HIGH"}],
        "metadata": {"llm_requested": False, "skillspector_version": "2.1.5"},
    }

    def fake_run(command, text, capture_output, check, env):
        output_index = command.index("--output") + 1
        Path(command[output_index]).write_text(json.dumps(report))
        return subprocess.CompletedProcess(command, 1, stdout="Report saved", stderr="")

    monkeypatch.setattr(skillspector, "resolve_skillspector_binary", lambda: "skillspector")
    monkeypatch.setattr(skillspector.subprocess, "run", fake_run)

    assert skillspector.run_skillspector(tmp_path, tmp_path / "report.json") == report


def test_run_skillspector_fails_without_report(monkeypatch, tmp_path: Path):
    def fake_run(command, text, capture_output, check, env):
        return subprocess.CompletedProcess(command, 2, stdout="", stderr="boom")

    monkeypatch.setattr(skillspector, "resolve_skillspector_binary", lambda: "skillspector")
    monkeypatch.setattr(skillspector.subprocess, "run", fake_run)

    with pytest.raises(RuntimeError, match="boom"):
        skillspector.run_skillspector(tmp_path, tmp_path / "report.json")


def test_skillspector_env_maps_generic_llm_env(monkeypatch):
    monkeypatch.setenv("SKILL_EXCHANGE_LLM_API_KEY", "secret-value")
    monkeypatch.setenv("SKILL_EXCHANGE_LLM_BASE_URL", "https://llm.example/v1")
    monkeypatch.setenv("SKILL_EXCHANGE_LLM_MODEL", "gpt-5")
    monkeypatch.setenv("SKILL_EXCHANGE_LLM_PROVIDER", "openai")
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_BASE_URL", raising=False)
    monkeypatch.delenv("SKILLSPECTOR_PROVIDER", raising=False)
    monkeypatch.delenv("SKILLSPECTOR_MODEL", raising=False)

    env = skillspector.skillspector_env()
    config = skillspector.skillspector_llm_config()

    assert env["OPENAI_API_KEY"] == "secret-value"
    assert env["OPENAI_BASE_URL"] == "https://llm.example/v1"
    assert config == {"provider": "openai", "model": "gpt-5"}


def test_mitre_specific_llm_env_names_are_not_committed():
    root = Path(__file__).resolve().parents[1]
    old_prefix = "MDEV" + "CHAT"
    checked_paths = [
        root / "scripts" / "skill_exchange" / "skillspector.py",
        root / "docs" / "ci.md",
        root / "docs" / "local-mvp.md",
    ]

    assert all(old_prefix not in path.read_text() for path in checked_paths)
