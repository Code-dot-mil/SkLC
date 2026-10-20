import io
import json
import shutil
import subprocess
import urllib.request
from pathlib import Path

import pytest


@pytest.fixture
def skill(tmp_path):
    path = tmp_path / "my-skill"
    path.mkdir()
    (path / "SKILL.md").write_text("---\nname: my-skill\ndescription: Example\n---\nInstructions.\n")
    return path


@pytest.fixture
def gateway(monkeypatch):
    for key in ("SKILLSPECTOR_COMPAT_BASE_URL", "SKILLSPECTOR_COMPAT_API_KEY", "AZURE_OPENAI_ENDPOINT",
                "AZURE_OPENAI_API_KEY", "AZURE_OPENAI_DEPLOYMENT", "AZURE_OPENAI_API_VERSION", "OPENAI_PROJECT_ID"):
        monkeypatch.delenv(key, raising=False)
    monkeypatch.setenv("SKILLSPECTOR_PROVIDER", "openai")
    monkeypatch.setenv("SKILLSPECTOR_MODEL", "review-model")
    monkeypatch.setenv("OPENAI_BASE_URL", "https://gateway.example/v1")
    monkeypatch.setenv("OPENAI_API_KEY", "test-secret")
    state = {"calls": [], "overrides": {}, "finish_reason": "stop"}

    def complete(opener, request, *, timeout):
        state["calls"].append(request)
        if "error" in state:
            raise state["error"]
        payload = json.loads(request.data)
        evidence = json.loads(payload["messages"][1]["content"])
        result = {
            "safe_to_use": True, "summary": "Benign examples.",
            "coverage_sufficient": True, "coverage_reason": "Supplied context is sufficient.",
            "findings": [{"index": index, "rule_id": issue["id"], "determination": "false_positive",
                          "reason": "Illustrative example."}
                         for index, issue in enumerate(evidence["report"]["issues"], 1)],
        }
        result.update(state["overrides"])
        content = state.get("content", json.dumps(result))
        response = {"model": "served-model", "choices": [{"finish_reason": state["finish_reason"],
                                                          "message": {"content": content}}]}
        if "usage" in state:
            response["usage"] = state["usage"]
        return io.BytesIO(json.dumps(response).encode())

    monkeypatch.setattr(urllib.request.OpenerDirector, "open", complete)
    return state


@pytest.fixture
def scanner(monkeypatch, gateway):
    report = {
        "execution_successful": True,
        "analysis_completeness": {"is_complete": True},
        "metadata": {"llm_requested": True, "llm_available": True},
        "risk_assessment": {"score": 80, "severity": "HIGH"},
        "issues": [{"id": "CE1", "severity": "HIGH", "location": {"file": "run.py", "start_line": 3},
                    "explanation": "Untrusted input reaches eval", "remediation": "Parse data without eval"}],
    }
    state = {"report": report, "status": 1, "calls": [], "timeouts": []}

    def scan(command, *, stdout, **kwargs):
        state["calls"].append(command)
        state["timeouts"].append(kwargs["timeout"])
        stdout.write("scanner diagnostics\n")
        path = Path(command[command.index("--output") + 1])
        if state["report"] is not None:
            path.write_text(state.get("native", json.dumps(state["report"])), encoding="utf-8")
        if "error" in state:
            raise state["error"]
        return subprocess.CompletedProcess(command, state["status"])

    monkeypatch.setattr(shutil, "which", lambda command: "/scanner-bin/skillspector")
    monkeypatch.setattr(subprocess, "run", scan)
    return state
