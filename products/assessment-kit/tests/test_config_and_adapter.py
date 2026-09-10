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


def test_version_check_rejects_other_versions(monkeypatch):
    monkeypatch.setattr(
        subprocess,
        "run",
        lambda *args, **kwargs: subprocess.CompletedProcess(args[0], 0, "skillspector v2.11.0", ""),
    )

    with pytest.raises(AssessmentError, match="required 2.10.0"):
        require_supported_version("skillspector")


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
