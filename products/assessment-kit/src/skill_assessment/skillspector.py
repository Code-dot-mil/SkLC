from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import tempfile
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .config import SkillSpectorConfig
from .errors import AssessmentError, RetryableAssessmentError

SUPPORTED_SKILLSPECTOR_VERSION = "2.10.0"


@dataclass(frozen=True)
class NativeReport:
    content: bytes
    parsed: dict[str, Any]
    diagnostics: str = ""


def resolve_binary(environ: Mapping[str, str] | None = None) -> str:
    env = os.environ if environ is None else environ
    configured = env.get("SKILLSPECTOR_BIN", "").strip()
    if configured:
        path = Path(configured).expanduser()
        if not path.exists() or not path.is_file():
            raise AssessmentError(f"SKILLSPECTOR_BIN is not an executable file: {path}")
        if not os.access(path, os.X_OK):
            raise AssessmentError(f"SKILLSPECTOR_BIN is not executable: {path}")
        return str(path)
    found = shutil.which("skillspector")
    if not found:
        raise AssessmentError("skillspector executable not found; set SKILLSPECTOR_BIN or add it to PATH")
    return found


def _normalized_version(output: str) -> str:
    matches = re.findall(r"(?<!\d)v?(\d+\.\d+\.\d+)(?!\d)", output)
    return matches[-1] if matches else ""


def require_supported_version(binary: str) -> None:
    try:
        completed = subprocess.run(
            [binary, "--version"], capture_output=True, text=True, check=False, timeout=30
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise AssessmentError("could not determine SkillSpector version") from exc
    detected = _normalized_version(f"{completed.stdout}\n{completed.stderr}")
    if completed.returncode != 0 or detected != SUPPORTED_SKILLSPECTOR_VERSION:
        label = detected or "unknown"
        raise AssessmentError(
            f"unsupported SkillSpector version {label}; required {SUPPORTED_SKILLSPECTOR_VERSION}"
        )


def _process_environment(config: SkillSpectorConfig, environ: Mapping[str, str] | None = None) -> dict[str, str]:
    env = dict(os.environ if environ is None else environ)
    native_names = (
        "SKILLSPECTOR_PROVIDER",
        "SKILLSPECTOR_COMPAT_API_KEY",
        "SKILLSPECTOR_COMPAT_BASE_URL",
        "SKILLSPECTOR_MODEL",
    )
    if config.scan_mode == "llm-assisted":
        env.update(
            {
                "SKILLSPECTOR_PROVIDER": config.llm_provider or "",
                "SKILLSPECTOR_COMPAT_API_KEY": config.llm_api_key or "",
                "SKILLSPECTOR_COMPAT_BASE_URL": config.llm_base_url or "",
                "SKILLSPECTOR_MODEL": config.llm_model or "",
            }
        )
    else:
        for name in native_names:
            env.pop(name, None)
    return env


def _diagnostic(completed: subprocess.CompletedProcess[str], config: SkillSpectorConfig) -> str:
    detail = "\n".join(part.strip() for part in (completed.stdout, completed.stderr) if part.strip())
    secrets = [config.llm_api_key]
    secrets.extend(
        value
        for name, value in os.environ.items()
        if value and any(fragment in name.upper() for fragment in ("API_KEY", "TOKEN", "SECRET", "PASSWORD"))
    )
    for secret in secrets:
        if secret:
            detail = detail.replace(secret, "[REDACTED]")
    return detail[:2000] or f"SkillSpector exited {completed.returncode}"


def _validate_report(content: bytes, config: SkillSpectorConfig, returncode: int) -> dict[str, Any]:
    try:
        parsed = json.loads(content)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise AssessmentError("SkillSpector did not produce a valid JSON object") from exc
    if not isinstance(parsed, dict):
        raise AssessmentError("SkillSpector did not produce a JSON object")
    metadata = parsed.get("metadata")
    if not isinstance(metadata, dict):
        raise AssessmentError("SkillSpector report is missing metadata")
    if str(metadata.get("skillspector_version", "")).removeprefix("v") != SUPPORTED_SKILLSPECTOR_VERSION:
        raise AssessmentError("SkillSpector report identifies an unsupported version")
    if returncode not in {0, 1} or parsed.get("execution_successful") is not True:
        raise AssessmentError("SkillSpector scan did not complete successfully")
    if config.scan_mode == "llm-assisted" and (
        metadata.get("llm_requested") is not True
        or metadata.get("llm_available") is not True
        or metadata.get("llm_degraded") is True
    ):
        raise RetryableAssessmentError("SkillSpector report has degraded or unavailable LLM coverage")
    return parsed


def run(skill_path: Path, config: SkillSpectorConfig, *, binary: str, output_root: Path) -> NativeReport:
    output_root_existed = output_root.exists()
    try:
        output_root.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        raise AssessmentError(f"cannot create command output directory {output_root}: {exc}") from exc
    try:
        temporary_directory = Path(tempfile.mkdtemp(prefix=".skill-assessment-", dir=output_root))
    except OSError as exc:
        if not output_root_existed:
            try:
                output_root.rmdir()
            except OSError:
                pass
        raise AssessmentError(f"cannot create temporary assessor output beneath {output_root}: {exc}") from exc
    output_path = temporary_directory / "report.json"
    command = [binary, "scan", str(skill_path), "--format", "json", "--output", str(output_path)]
    if config.scan_mode == "static-only":
        command.append("--no-llm")
    try:
        try:
            completed = subprocess.run(
                command,
                capture_output=True,
                text=True,
                check=False,
                timeout=config.timeout_seconds,
                env=_process_environment(config),
            )
        except subprocess.TimeoutExpired as exc:
            raise RetryableAssessmentError(
                f"SkillSpector timed out after {config.timeout_seconds} seconds"
            ) from exc
        except OSError as exc:
            raise AssessmentError(f"could not run SkillSpector: {exc}") from exc

        if not output_path.is_file():
            detail = _diagnostic(completed, config)
            error_type = (
                RetryableAssessmentError
                if config.scan_mode == "llm-assisted" and "429" in detail
                else AssessmentError
            )
            raise error_type(f"SkillSpector produced no report: {detail}")
        try:
            content = output_path.read_bytes()
        except OSError as exc:
            raise AssessmentError("could not read SkillSpector report") from exc
        try:
            parsed = _validate_report(content, config, completed.returncode)
        except AssessmentError as exc:
            if (
                config.scan_mode == "llm-assisted"
                and "429" in _diagnostic(completed, config)
                and not isinstance(exc, RetryableAssessmentError)
            ):
                raise RetryableAssessmentError(str(exc)) from exc
            raise
        return NativeReport(content=content, parsed=parsed, diagnostics=_diagnostic(completed, config))
    finally:
        shutil.rmtree(temporary_directory, ignore_errors=True)
        if not output_root_existed:
            try:
                output_root.rmdir()
            except OSError:
                pass
