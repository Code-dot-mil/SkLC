from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

from skill_assessment.config import SkillSpectorConfig, load_skillspector_config
from skill_assessment.errors import AssessmentError
from skill_assessment.skillspector import _process_environment, require_supported_version, run


def test_config_environment_overrides_file(tmp_path: Path):
    path = tmp_path / "config.json"
    path.write_text(json.dumps({"assessors": {"skillspector": {"scan_mode": "static-only", "timeout_seconds": 4}}}))

    config = load_skillspector_config(
        path,
        {
            "SKLC_SKILLSPECTOR_SCAN_MODE": "llm-assisted",
            "SKLC_SKILLSPECTOR_TIMEOUT_SECONDS": "9",
            "SKLC_LLM_PROVIDER": "openai_compatible",
            "SKLC_LLM_API_KEY": "secret",
            "SKLC_LLM_BASE_URL": "https://example.invalid/v1",
            "SKLC_LLM_MODEL": "model",
        },
    )

    assert config.scan_mode == "llm-assisted"
    assert config.timeout_seconds == 9


def test_config_rejects_unknown_keys(tmp_path: Path):
    path = tmp_path / "config.json"
    path.write_text(json.dumps({"assessors": {"skillspector": {"native_config": "unexpected"}}}))

    with pytest.raises(AssessmentError, match="unsupported skillspector setting"):
        load_skillspector_config(path, {})


def test_llm_environment_overrides_ambient_native_values():
    config = SkillSpectorConfig(
        scan_mode="llm-assisted",
        timeout_seconds=600,
        llm_provider="openai_compatible",
        llm_api_key="selected-secret",
        llm_base_url="https://selected.invalid/v1",
        llm_model="selected-model",
    )

    result = _process_environment(
        config,
        {
            "SKILLSPECTOR_PROVIDER": "ambient",
            "SKILLSPECTOR_COMPAT_API_KEY": "ambient-secret",
            "SKILLSPECTOR_COMPAT_BASE_URL": "https://ambient.invalid",
            "SKILLSPECTOR_MODEL": "ambient-model",
        },
    )

    assert result["SKILLSPECTOR_PROVIDER"] == "openai_compatible"
    assert result["SKILLSPECTOR_COMPAT_API_KEY"] == "selected-secret"
    assert result["SKILLSPECTOR_COMPAT_BASE_URL"] == "https://selected.invalid/v1"
    assert result["SKILLSPECTOR_MODEL"] == "selected-model"


def test_static_invocation_uses_positional_path_and_no_llm(monkeypatch, tmp_path: Path):
    seen: list[str] = []

    def fake_run(command, **kwargs):
        seen.extend(command)
        output = Path(command[command.index("--output") + 1])
        output.write_text(
            json.dumps(
                {
                    "execution_successful": True,
                    "metadata": {"skillspector_version": "2.10.0", "llm_requested": False},
                }
            )
        )
        return subprocess.CompletedProcess(command, 1, "", "")

    monkeypatch.setattr(subprocess, "run", fake_run)
    skill = tmp_path / "skill"
    skill.mkdir()

    report = run(
        skill,
        SkillSpectorConfig(scan_mode="static-only", timeout_seconds=5),
        binary="skillspector",
        output_root=tmp_path / "output",
    )

    assert seen[:3] == ["skillspector", "scan", str(skill)]
    assert "--no-llm" in seen
    native_output = Path(seen[seen.index("--output") + 1])
    assert native_output.is_relative_to(tmp_path / "output")
    assert report.parsed["execution_successful"] is True


def test_static_environment_removes_ambient_llm_configuration():
    config = SkillSpectorConfig(scan_mode="static-only", timeout_seconds=600)

    result = _process_environment(
        config,
        {
            "UNCHANGED": "value",
            "SKILLSPECTOR_PROVIDER": "ambient",
            "SKILLSPECTOR_COMPAT_API_KEY": "ambient-secret",
            "SKILLSPECTOR_COMPAT_BASE_URL": "https://ambient.invalid",
            "SKILLSPECTOR_MODEL": "ambient-model",
        },
    )

    assert result == {"UNCHANGED": "value"}


@pytest.mark.parametrize("version", ["2.11.0", "2.10.0rc1", "2.10.0-dev", "2.10.0.post1"])
def test_version_check_rejects_unsupported_versions(monkeypatch, version):
    monkeypatch.setattr(
        subprocess, "run",
        lambda *args, **kwargs: subprocess.CompletedProcess(args[0], 0, f"SkillSpector v{version}", ""),
    )
    with pytest.raises(AssessmentError, match="unsupported"):
        require_supported_version("skillspector")


@pytest.mark.parametrize("value", [True, 0, -1, 1.5, float("inf"), None, [], {}])
def test_invalid_timeout_is_a_configuration_error(tmp_path, value):
    path = tmp_path / "config.json"
    path.write_text(json.dumps({"assessors": {"skillspector": {"timeout_seconds": value}}}))
    with pytest.raises(AssessmentError, match="positive integer"):
        load_skillspector_config(path, {})


@pytest.mark.parametrize("failure,expected_exit", [
    ("timeout", 10), ("rate-limit", 10), ("long-rate-limit", 10),
    ("temporary", 10), ("no-report", 2), ("malformed", 2),
    ("exit-two", 2), ("unsuccessful", 2), ("wrong-version", 2),
    ("llm-unavailable", 10), ("llm-not-requested", 10), ("failed-degraded", 10),
])
def test_failed_adapter_keeps_no_output_and_redacts_secrets(monkeypatch, tmp_path, failure, expected_exit):
    config = SkillSpectorConfig(
        "llm-assisted", 1, "openai_compatible", "private-key", "https://example.invalid", "model"
    )

    def execute(command, **kwargs):
        if failure == "timeout":
            raise subprocess.TimeoutExpired(command, 1)
        if failure in {"rate-limit", "long-rate-limit", "temporary", "no-report"}:
            detail = "HTTP 429 private-key" if "rate-limit" in failure else "bad"
            stdout = "private-key " + "log " * 1000 if failure == "long-rate-limit" else ""
            return subprocess.CompletedProcess(command, 75 if failure == "temporary" else 2, stdout, detail)
        report = {
            "execution_successful": failure not in {"unsuccessful", "failed-degraded"},
            "metadata": {
                "skillspector_version": "3.0.0" if failure == "wrong-version" else "2.10.0",
                "llm_requested": failure != "llm-not-requested",
                "llm_available": failure != "llm-unavailable",
                "llm_degraded": failure == "failed-degraded",
            },
        }
        output = Path(command[command.index("--output") + 1])
        output.write_text("malformed" if failure == "malformed" else json.dumps(report))
        return subprocess.CompletedProcess(command, 2 if failure == "exit-two" else 0, "private-key", "")

    monkeypatch.setattr(subprocess, "run", execute)
    with pytest.raises(AssessmentError) as caught:
        run(tmp_path, config, binary="skillspector", output_root=tmp_path / "output")
    assert caught.value.exit_code == expected_exit
    assert "private-key" not in str(caught.value)
    assert not (tmp_path / "output").exists()


def test_successful_llm_report_is_retained_unchanged(monkeypatch, tmp_path):
    content = (
        b'{ "execution_successful": true, "metadata": {"skillspector_version": "2.10.0",'
        b' "llm_requested": true, "llm_available": true}}\n'
    )
    calls = []

    def execute(command, **kwargs):
        calls.append(command)
        Path(command[command.index("--output") + 1]).write_bytes(content)
        return subprocess.CompletedProcess(command, 1, "", "")

    monkeypatch.setattr(subprocess, "run", execute)
    result = run(
        tmp_path,
        SkillSpectorConfig("llm-assisted", 600, "openai_compatible", "key", "https://example.invalid", "model"),
        binary="skillspector", output_root=tmp_path / "output",
    )
    assert result.content == content
    assert len(calls) == 1 and "--no-llm" not in calls[0]


def test_explicit_binary_path_resolves_from_current_directory(tmp_path, monkeypatch):
    from skill_assessment.skillspector import resolve_binary

    binary = tmp_path / "scanner"
    binary.write_text("#!/bin/sh\nexit 0\n")
    binary.chmod(0o755)
    monkeypatch.chdir(tmp_path)
    assert resolve_binary({"SKILLSPECTOR_BIN": "./scanner"}) == str(binary)


def test_blank_binary_override_does_not_select_path():
    from skill_assessment.skillspector import resolve_binary

    with pytest.raises(AssessmentError, match="must not be blank"):
        resolve_binary({"SKILLSPECTOR_BIN": " "})
