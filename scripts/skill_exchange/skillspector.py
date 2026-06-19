from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path
from typing import Any


def load_fixture_report(name: str) -> dict[str, Any]:
    path = Path(".gitlab-mock/fixtures") / name
    return json.loads(path.read_text())


def run_skillspector(skill_path: Path, output_path: Path, *, no_llm: bool = True) -> dict[str, Any]:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    binary = shutil.which("skillspector")
    if binary is None:
        report = {
            "scanner": {"name": "skillspector", "version": "unavailable"},
            "mode": "static-only" if no_llm else "llm-assisted",
            "findings": [],
            "error": "skillspector_not_found",
        }
        output_path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
        return report

    command = [binary, "scan", str(skill_path), "--format", "json", "--output", str(output_path)]
    if no_llm:
        command.append("--no-llm")
    completed = subprocess.run(command, text=True, capture_output=True, check=False)
    if output_path.exists():
        return json.loads(output_path.read_text())

    report = {
        "scanner": {"name": "skillspector", "version": "unknown"},
        "mode": "static-only" if no_llm else "llm-assisted",
        "findings": [],
        "error": completed.stderr or completed.stdout or f"skillspector exited {completed.returncode}",
    }
    output_path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    return report
