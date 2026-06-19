from __future__ import annotations

import json
import os
import posixpath
import shutil
import subprocess
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


def skillspector_env() -> dict[str, str]:
    env = os.environ.copy()
    if "MDEVCHAT_API_KEY" not in env:
        return env

    base_url = env.get("MDEVCHAT_BASE_URL", "").strip()
    model = env.get("MDEVCHAT_LLM_MODEL", "").strip()
    if base_url and model and not env.get("OPENAI_BASE_URL"):
        env["OPENAI_BASE_URL"] = posixpath.join(base_url.rstrip("/"), "deployments", model) + "/"
    if model and not env.get("SKILLSPECTOR_MODEL"):
        env["SKILLSPECTOR_MODEL"] = model
    env.setdefault("SKILLSPECTOR_PROVIDER", "openai")
    env.setdefault("OPENAI_API_KEY", "unused")
    return env


def skillspector_llm_config() -> dict[str, str | None]:
    env = skillspector_env()
    return {
        "provider": env.get("SKILLSPECTOR_PROVIDER"),
        "model": env.get("SKILLSPECTOR_MODEL"),
    }
