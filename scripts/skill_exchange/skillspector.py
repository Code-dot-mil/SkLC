from __future__ import annotations

import json
import os
import shutil
import subprocess
from hashlib import sha256
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path
from typing import Any


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
    command = [binary, "scan", str(skill_path), "--format", "json", "--output", str(output_path)]
    if no_llm:
        command.append("--no-llm")
    completed = subprocess.run(command, text=True, capture_output=True, check=False, env=skillspector_env())
    if output_path.exists():
        return json.loads(output_path.read_text())

    output = completed.stderr or completed.stdout or f"skillspector exited {completed.returncode}"
    raise RuntimeError(output)


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
    endpoint = (
        env.get("AZURE_OPENAI_ENDPOINT")
        if provider == "azure_openai"
        else env.get("OPENAI_BASE_URL") if provider == "openai" else None
    )
    return {
        "provider": provider,
        "model": env.get("SKILLSPECTOR_MODEL"),
        "deployment": env.get("AZURE_OPENAI_DEPLOYMENT") if provider == "azure_openai" else None,
        "api_version": env.get("AZURE_OPENAI_API_VERSION") if provider == "azure_openai" else None,
        "endpoint_hash": sha256(endpoint.encode()).hexdigest() if endpoint else None,
    }
