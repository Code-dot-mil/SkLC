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


def test_skillspector_llm_config_uses_sanitized_mdevchat_env(monkeypatch):
    monkeypatch.setenv("MDEVCHAT_API_KEY", "secret-value")
    monkeypatch.setenv("MDEVCHAT_BASE_URL", "https://mdevchat.example/openai/")
    monkeypatch.setenv("MDEVCHAT_LLM_MODEL", "gpt-5")
    monkeypatch.delenv("SKILLSPECTOR_PROVIDER", raising=False)
    monkeypatch.delenv("SKILLSPECTOR_MODEL", raising=False)

    config = skillspector.skillspector_llm_config()

    assert config == {"provider": "openai", "model": "gpt-5"}
