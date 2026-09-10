import json
import subprocess
import sys
from pathlib import Path

import pytest
from skill_exchange import skillspector, skillspector_runner


def test_run_skillspector_accepts_finding_exit_code_with_valid_report(monkeypatch, tmp_path: Path):
    report = {
        "execution_successful": True,
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


def test_run_skillspector_rejects_failed_execution_and_preserves_report(monkeypatch, tmp_path: Path):
    report = {
        "execution_successful": False,
        "risk_assessment": {"score": 100, "severity": "CRITICAL", "recommendation": "DO_NOT_INSTALL"},
        "issues": [{"id": "E2", "severity": "HIGH"}],
        "metadata": {"llm_requested": True, "skillspector_version": "2.1.5"},
    }
    report_path = tmp_path / "report.json"

    def fake_run(command, text, capture_output, check, env):
        Path(command[command.index("--output") + 1]).write_text(json.dumps(report))
        return subprocess.CompletedProcess(command, 2, stdout="", stderr="OpenAIModelNotFoundError")

    monkeypatch.setattr(skillspector, "resolve_skillspector_binary", lambda: "skillspector")
    monkeypatch.setattr(skillspector.subprocess, "run", fake_run)

    with pytest.raises(
        skillspector.SkillSpectorExecutionError,
        match="execution_successful=false: OpenAIModelNotFoundError",
    ) as error:
        skillspector.run_skillspector(tmp_path, report_path, no_llm=False)

    assert error.value.report == report
    assert json.loads(report_path.read_text()) == report


def test_run_skillspector_fails_without_report(monkeypatch, tmp_path: Path):
    def fake_run(command, text, capture_output, check, env):
        return subprocess.CompletedProcess(command, 2, stdout="", stderr="boom")

    monkeypatch.setattr(skillspector, "resolve_skillspector_binary", lambda: "skillspector")
    monkeypatch.setattr(skillspector.subprocess, "run", fake_run)

    with pytest.raises(RuntimeError, match="boom"):
        skillspector.run_skillspector(tmp_path, tmp_path / "report.json")


def test_skillspector_version_normalizes_leading_v_from_binary(monkeypatch):
    def missing_package_version(package_name):
        raise skillspector.PackageNotFoundError

    def fake_run(command, text, capture_output, check):
        return subprocess.CompletedProcess(command, 0, stdout="skillspector v2.1.5\n", stderr="")

    monkeypatch.setattr(skillspector, "version", missing_package_version)
    monkeypatch.setattr(skillspector.shutil, "which", lambda name: "/usr/local/bin/skillspector")
    monkeypatch.setattr(skillspector.subprocess, "run", fake_run)

    assert skillspector.skillspector_version() == "2.1.5"


def test_skillspector_command_uses_header_adapter_only_for_llm_scans():
    env = {"SKILL_EXCHANGE_LLM_API_KEY_HEADER": "api-key"}
    scanner_args = ["scan", "skill", "--format", "json"]

    assert skillspector.skillspector_command("skillspector", scanner_args, env=env, no_llm=False) == [
        sys.executable,
        "-m",
        "skill_exchange.skillspector_runner",
        *scanner_args,
    ]
    assert skillspector.skillspector_command("skillspector", scanner_args, env=env, no_llm=True) == [
        "skillspector",
        *scanner_args,
    ]


def test_skillspector_adapter_rejects_invalid_header_name(monkeypatch):
    monkeypatch.setenv("SKILL_EXCHANGE_LLM_API_KEY_HEADER", "Bad Header")

    with pytest.raises(RuntimeError, match="valid HTTP header name"):
        skillspector_runner.configure_openai_compatible_provider()


def test_skillspector_adapter_requires_compatible_provider_and_key(monkeypatch):
    monkeypatch.setenv("SKILL_EXCHANGE_LLM_API_KEY_HEADER", "X-Api-Key")
    monkeypatch.setenv("SKILLSPECTOR_PROVIDER", "openai")

    with pytest.raises(RuntimeError, match="require the openai_compatible provider"):
        skillspector_runner.configure_openai_compatible_provider()

    monkeypatch.setenv("SKILLSPECTOR_PROVIDER", "openai_compatible")
    monkeypatch.delenv("SKILLSPECTOR_COMPAT_API_KEY", raising=False)
    with pytest.raises(RuntimeError, match="require SKILL_EXCHANGE_LLM_API_KEY"):
        skillspector_runner.configure_openai_compatible_provider()


def test_skillspector_adapter_rejects_invalid_request_rate(monkeypatch):
    monkeypatch.setenv("SKILL_EXCHANGE_LLM_REQUESTS_PER_SECOND", "zero")
    monkeypatch.setenv("SKILLSPECTOR_PROVIDER", "openai_compatible")
    monkeypatch.setenv("SKILLSPECTOR_COMPAT_API_KEY", "secret")

    with pytest.raises(RuntimeError, match="must be a number"):
        skillspector_runner.configure_openai_compatible_provider()

    monkeypatch.setenv("SKILL_EXCHANGE_LLM_REQUESTS_PER_SECOND", "0")
    with pytest.raises(RuntimeError, match="must be greater than zero"):
        skillspector_runner.configure_openai_compatible_provider()


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
    assert config == {
        "provider": "openai",
        "model": "gpt-5",
        "deployment": None,
        "api_version": None,
        "api_key_header": None,
        "requests_per_second": None,
        "endpoint_hash": "d5e402bf7bacd64a5aa920e05315e0f106363e00c2fd868856660c607ce4ae22",
    }


def test_skillspector_env_maps_generic_openai_compatible_env(monkeypatch):
    monkeypatch.setenv("SKILL_EXCHANGE_LLM_API_KEY", "gateway-secret")
    monkeypatch.setenv("SKILL_EXCHANGE_LLM_BASE_URL", "https://mdevchat.apim.mitre.org/openai/v1")
    monkeypatch.setenv("SKILL_EXCHANGE_LLM_MODEL", "gpt-5.5")
    monkeypatch.setenv("SKILL_EXCHANGE_LLM_PROVIDER", "openai_compatible")
    monkeypatch.setenv("SKILL_EXCHANGE_LLM_API_KEY_HEADER", "api-key")
    monkeypatch.setenv("SKILL_EXCHANGE_LLM_REQUESTS_PER_SECOND", "0.1")
    for name in (
        "SKILLSPECTOR_COMPAT_API_KEY",
        "SKILLSPECTOR_COMPAT_BASE_URL",
        "OPENAI_API_KEY",
        "OPENAI_BASE_URL",
        "AZURE_OPENAI_API_KEY",
        "AZURE_OPENAI_ENDPOINT",
        "SKILLSPECTOR_PROVIDER",
        "SKILLSPECTOR_MODEL",
    ):
        monkeypatch.delenv(name, raising=False)

    env = skillspector.skillspector_env()
    config = skillspector.skillspector_llm_config()

    assert env["SKILLSPECTOR_PROVIDER"] == "openai_compatible"
    assert env["SKILLSPECTOR_COMPAT_API_KEY"] == "gateway-secret"
    assert env["SKILLSPECTOR_COMPAT_BASE_URL"] == "https://mdevchat.apim.mitre.org/openai/v1"
    assert env["SKILLSPECTOR_MODEL"] == "gpt-5.5"
    assert "OPENAI_API_KEY" not in env
    assert "AZURE_OPENAI_API_KEY" not in env
    assert config == {
        "provider": "openai_compatible",
        "model": "gpt-5.5",
        "deployment": None,
        "api_version": None,
        "api_key_header": "api-key",
        "requests_per_second": "0.1",
        "endpoint_hash": "55a0ebce3878ccee9dd6f6e9f65f6eeeec216aaf696b2c19fb144f1762c8d6cf",
    }


def test_skillspector_env_maps_generic_azure_openai_env(monkeypatch):
    monkeypatch.setenv("SKILL_EXCHANGE_LLM_API_KEY", "azure-secret")
    monkeypatch.setenv("SKILL_EXCHANGE_LLM_BASE_URL", "https://example.openai.azure.com/")
    monkeypatch.setenv("SKILL_EXCHANGE_LLM_MODEL", "gpt-5")
    monkeypatch.setenv("SKILL_EXCHANGE_LLM_PROVIDER", "azure_openai")
    monkeypatch.setenv("SKILL_EXCHANGE_LLM_DEPLOYMENT", "production-gpt-5")
    monkeypatch.setenv("SKILL_EXCHANGE_LLM_API_VERSION", "2025-04-01-preview")
    for name in (
        "AZURE_OPENAI_API_KEY",
        "AZURE_OPENAI_ENDPOINT",
        "AZURE_OPENAI_DEPLOYMENT",
        "AZURE_OPENAI_API_VERSION",
        "OPENAI_API_KEY",
        "OPENAI_BASE_URL",
        "SKILLSPECTOR_PROVIDER",
        "SKILLSPECTOR_MODEL",
    ):
        monkeypatch.delenv(name, raising=False)

    env = skillspector.skillspector_env()
    config = skillspector.skillspector_llm_config()

    assert env["SKILLSPECTOR_PROVIDER"] == "azure_openai"
    assert env["AZURE_OPENAI_API_KEY"] == "azure-secret"
    assert env["AZURE_OPENAI_ENDPOINT"] == "https://example.openai.azure.com/"
    assert env["AZURE_OPENAI_DEPLOYMENT"] == "production-gpt-5"
    assert env["AZURE_OPENAI_API_VERSION"] == "2025-04-01-preview"
    assert env["SKILLSPECTOR_MODEL"] == "gpt-5"
    assert "OPENAI_API_KEY" not in env
    assert "OPENAI_BASE_URL" not in env
    assert config == {
        "provider": "azure_openai",
        "model": "gpt-5",
        "deployment": "production-gpt-5",
        "api_version": "2025-04-01-preview",
        "api_key_header": None,
        "requests_per_second": None,
        "endpoint_hash": "7bef302251509c8f87385679f5607976a809a9bd5d5433860114b812bb5bd8dd",
    }


def test_native_azure_openai_env_wins_over_generic_env(monkeypatch):
    monkeypatch.setenv("SKILL_EXCHANGE_LLM_API_KEY", "generic-secret")
    monkeypatch.setenv("SKILL_EXCHANGE_LLM_BASE_URL", "https://generic.example/")
    monkeypatch.setenv("SKILL_EXCHANGE_LLM_PROVIDER", "openai")
    monkeypatch.setenv("SKILLSPECTOR_PROVIDER", "azure_openai")
    monkeypatch.setenv("AZURE_OPENAI_API_KEY", "native-secret")
    monkeypatch.setenv("AZURE_OPENAI_ENDPOINT", "https://native.openai.azure.com/")
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_BASE_URL", raising=False)

    env = skillspector.skillspector_env()

    assert env["SKILLSPECTOR_PROVIDER"] == "azure_openai"
    assert env["AZURE_OPENAI_API_KEY"] == "native-secret"
    assert env["AZURE_OPENAI_ENDPOINT"] == "https://native.openai.azure.com/"
    assert "OPENAI_API_KEY" not in env
    assert "OPENAI_BASE_URL" not in env


def test_legacy_provider_specific_llm_env_names_are_not_committed():
    root = Path(__file__).resolve().parents[1]
    old_prefix = "MDEV" + "CHAT"
    checked_paths = [
        root / "scripts" / "skill_exchange" / "skillspector.py",
        root / "CI.md",
        root / "README.md",
        root / "CONTRIBUTING.md",
    ]

    assert all(old_prefix not in path.read_text() for path in checked_paths)
