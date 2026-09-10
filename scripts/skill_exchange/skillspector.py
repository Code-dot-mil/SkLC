from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from hashlib import sha256
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path
from typing import Any


class SkillSpectorExecutionError(RuntimeError):
    def __init__(self, message: str, *, report: dict[str, Any]) -> None:
        super().__init__(message)
        self.report = report


def resolve_skillspector_binary() -> str:
    configured = os.environ.get("SKILLSPECTOR_BIN")
    if configured:
        path = Path(configured).expanduser()
        if path.exists():
            return str(path)
        raise FileNotFoundError(f"SKILLSPECTOR_BIN does not exist: {path}")

    binary = shutil.which("skillspector")
    if binary:
        return binary

    raise FileNotFoundError("skillspector binary not found; set SKILLSPECTOR_BIN or add it to PATH")


def run_skillspector(skill_path: Path, output_path: Path, *, no_llm: bool = True) -> dict[str, Any]:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.unlink(missing_ok=True)
    binary = resolve_skillspector_binary()
    scanner_args = ["scan", str(skill_path), "--format", "json", "--output", str(output_path)]
    if no_llm:
        scanner_args.append("--no-llm")
    env = skillspector_env()
    command = skillspector_command(binary, scanner_args, env=env, no_llm=no_llm)
    completed = subprocess.run(command, text=True, capture_output=True, check=False, env=env)
    if output_path.exists():
        report = json.loads(output_path.read_text())
        if not isinstance(report, dict):
            raise RuntimeError("skillspector report must be a JSON object")
        if report.get("execution_successful") is False:
            detail = (completed.stderr or completed.stdout).strip()
            message = "skillspector reported execution_successful=false"
            if detail:
                message = f"{message}: {detail}"
            raise SkillSpectorExecutionError(message, report=report)
        return report

    output = completed.stderr or completed.stdout or f"skillspector exited {completed.returncode}"
    raise RuntimeError(output)


def skillspector_command(binary: str, scanner_args: list[str], *, env: dict[str, str], no_llm: bool) -> list[str]:
    api_key_header = env.get("SKILL_EXCHANGE_LLM_API_KEY_HEADER", "").strip()
    if api_key_header and not no_llm:
        return [sys.executable, "-m", "skill_exchange.skillspector_runner", *scanner_args]
    return [binary, *scanner_args]


def skillspector_version() -> str:
    try:
        return normalize_version(version("skillspector"))
    except PackageNotFoundError:
        pass

    binary = shutil.which("skillspector")
    if not binary:
        return "unknown"

    completed = subprocess.run([binary, "--version"], text=True, capture_output=True, check=False)
    output = (completed.stdout or completed.stderr).strip()
    return normalize_version(output.split()[-1]) if output else "unknown"


def normalize_version(version_value: str) -> str:
    version_value = version_value.strip()
    if len(version_value) > 1 and version_value.startswith("v") and version_value[1].isdigit():
        return version_value[1:]
    return version_value


def skillspector_env() -> dict[str, str]:
    env = os.environ.copy()

    api_key = env.get("SKILL_EXCHANGE_LLM_API_KEY", "").strip()
    base_url = env.get("SKILL_EXCHANGE_LLM_BASE_URL", "").strip()
    model = env.get("SKILL_EXCHANGE_LLM_MODEL", "").strip()
    provider = env.get("SKILL_EXCHANGE_LLM_PROVIDER", "").strip()
    deployment = env.get("SKILL_EXCHANGE_LLM_DEPLOYMENT", "").strip()
    api_version = env.get("SKILL_EXCHANGE_LLM_API_VERSION", "").strip()

    if provider and not env.get("SKILLSPECTOR_PROVIDER"):
        env["SKILLSPECTOR_PROVIDER"] = provider
    elif (api_key or base_url or model) and not env.get("SKILLSPECTOR_PROVIDER"):
        env["SKILLSPECTOR_PROVIDER"] = "openai"

    effective_provider = env.get("SKILLSPECTOR_PROVIDER", "").strip()
    if effective_provider == "azure_openai":
        set_if_missing(env, "AZURE_OPENAI_API_KEY", api_key)
        set_if_missing(env, "AZURE_OPENAI_ENDPOINT", base_url)
        set_if_missing(env, "AZURE_OPENAI_DEPLOYMENT", deployment)
        set_if_missing(env, "AZURE_OPENAI_API_VERSION", api_version)
    elif effective_provider == "openai_compatible":
        set_if_missing(env, "SKILLSPECTOR_COMPAT_API_KEY", api_key)
        set_if_missing(env, "SKILLSPECTOR_COMPAT_BASE_URL", base_url)
    elif effective_provider == "openai":
        set_if_missing(env, "OPENAI_API_KEY", api_key)
        set_if_missing(env, "OPENAI_BASE_URL", base_url)

    set_if_missing(env, "SKILLSPECTOR_MODEL", model)
    return env


def set_if_missing(env: dict[str, str], name: str, value: str) -> None:
    if value and not env.get(name):
        env[name] = value


def skillspector_llm_config() -> dict[str, str | None]:
    env = skillspector_env()
    provider = env.get("SKILLSPECTOR_PROVIDER")
    api_key_header = env.get("SKILL_EXCHANGE_LLM_API_KEY_HEADER", "").strip()
    endpoint = (
        env.get("AZURE_OPENAI_ENDPOINT")
        if provider == "azure_openai"
        else env.get("SKILLSPECTOR_COMPAT_BASE_URL")
        if provider == "openai_compatible"
        else env.get("OPENAI_BASE_URL")
        if provider == "openai"
        else None
    )
    return {
        "provider": provider,
        "model": env.get("SKILLSPECTOR_MODEL"),
        "deployment": env.get("AZURE_OPENAI_DEPLOYMENT") if provider == "azure_openai" else None,
        "api_version": env.get("AZURE_OPENAI_API_VERSION") if provider == "azure_openai" else None,
        "api_key_header": api_key_header if provider == "openai_compatible" and api_key_header else None,
        "endpoint_hash": sha256(endpoint.encode()).hexdigest() if endpoint else None,
    }
