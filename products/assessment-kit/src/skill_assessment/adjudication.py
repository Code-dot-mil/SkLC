"""Bounded SKILL.md adjudication through a configured chat-completions gateway."""

import json
import os
import time
import urllib.error
import urllib.request
from datetime import UTC, datetime
from importlib.resources import files
from pathlib import Path
from urllib.parse import quote, urlencode, urlsplit

from .errors import OutputDirectoryError

SCOPE = "MVP: examines SKILL.md and scanner evidence only; additional skill files are not independently reviewed."


class ConfigurationUnavailable(ValueError):
    """The requested gateway cannot be configured without changing providers."""


def gateway_config() -> tuple[str, str, str, dict[str, str]]:
    """Reuse documented SkillSpector environment settings, without importing it."""
    provider = os.environ.get("SKILLSPECTOR_PROVIDER", "").strip().lower()
    model = os.environ.get("SKILLSPECTOR_MODEL", "").strip()
    if provider == "openai":
        base = os.environ.get("OPENAI_BASE_URL", "").strip() or "https://api.openai.com/v1"
        key = os.environ.get("OPENAI_API_KEY", "").strip()
        url = base.rstrip("/") + "/chat/completions"
        headers = {"Authorization": "Bearer " + key}
        project = os.environ.get("OPENAI_PROJECT_ID", "").strip()
        if project:
            headers["OpenAI-Project"] = project
    elif provider == "openai_compatible":
        base = os.environ.get("SKILLSPECTOR_COMPAT_BASE_URL", "").strip()
        key = os.environ.get("SKILLSPECTOR_COMPAT_API_KEY", "").strip()
        url = base.rstrip("/") + "/chat/completions" if base else ""
        headers = {"Authorization": "Bearer " + key}
    elif provider == "azure_openai":
        base = os.environ.get("AZURE_OPENAI_ENDPOINT", "").strip()
        key = os.environ.get("AZURE_OPENAI_API_KEY", "").strip()
        deployment = os.environ.get("AZURE_OPENAI_DEPLOYMENT", "").strip() or model
        version = os.environ.get("AZURE_OPENAI_API_VERSION", "").strip() or "2024-06-01"
        url = (base.rstrip("/") + "/openai/deployments/" + quote(deployment, safe="")
               + "/chat/completions?" + urlencode({"api-version": version})) if base else ""
        headers = {"api-key": key}
    else:
        raise ConfigurationUnavailable("Adjudication requires openai, openai_compatible, or azure_openai provider.")
    if not key or not url or not model:
        raise ConfigurationUnavailable("Adjudication requires an explicit model and the selected gateway credentials.")
    parsed = urlsplit(url)
    if parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password:
        raise ConfigurationUnavailable("Adjudication requires an HTTPS gateway without credentials in its URL.")
    headers["Content-Type"] = "application/json"
    return provider, model, url, headers


def validate_verdict(result: object, issues: list[dict]) -> None:
    """Reject omitted findings, invented identities, and contradictory approvals."""
    keys = {"safe_to_use", "summary", "coverage_sufficient", "coverage_reason", "findings"}
    if not isinstance(result, dict) or set(result) != keys:
        raise ValueError("Unexpected adjudication fields")
    for key in ("safe_to_use", "coverage_sufficient"):
        if type(result[key]) is not bool:
            raise ValueError("Expected boolean")
    for key in ("summary", "coverage_reason"):
        if not isinstance(result[key], str) or not result[key].strip():
            raise ValueError("Expected rationale")
    verdicts = result["findings"]
    if not isinstance(verdicts, list) or len(verdicts) != len(issues):
        raise ValueError("Every issue must be adjudicated")
    for index, (verdict, issue) in enumerate(zip(verdicts, issues, strict=True), 1):
        if not isinstance(verdict, dict) or set(verdict) != {"index", "rule_id", "determination", "reason"}:
            raise ValueError("Unexpected finding fields")
        if (type(verdict["index"]) is not int or verdict["index"] != index
                or verdict["rule_id"] != issue.get("id", issue.get("rule_id"))):
            raise ValueError("Finding identity mismatch")
        if verdict["determination"] not in {"true_positive", "false_positive", "uncertain"}:
            raise ValueError("Unknown determination")
        if not isinstance(verdict["reason"], str) or not verdict["reason"].strip():
            raise ValueError("Missing finding rationale")
    if result["safe_to_use"] and (not result["coverage_sufficient"] or any(
        verdict["determination"] != "false_positive" for verdict in verdicts
    )):
        raise ValueError("Approval contradicts findings or coverage")


def not_adjudicated(issues: list[dict], reason: str) -> dict:
    """Unknown safety is distinct from an unsafe verdict."""
    return {
        "safe_to_use": None, "summary": reason, "coverage_sufficient": None, "coverage_reason": reason,
        "findings": [
            {"index": index, "rule_id": issue.get("id", issue.get("rule_id")),
             "determination": "not_adjudicated", "reason": reason}
            for index, issue in enumerate(issues, 1)
        ],
    }


class NoRedirect(urllib.request.HTTPRedirectHandler):
    """Do not forward credentials to a redirected endpoint."""

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def adjudicate_report(report: dict, skill_file: Path, output: Path, *, timeout: int = 300,
                      unavailable_reason: str | None = None) -> dict:
    """Save a validated verdict or an explicit failure, leaving the raw report unchanged."""
    started = time.monotonic()
    issues = report.get("issues", [])
    metadata = {
        "provider": os.environ.get("SKILLSPECTOR_PROVIDER", "").strip().lower() or None,
        "model": os.environ.get("SKILLSPECTOR_MODEL", "").strip() or None,
        "response_model": None, "created_at": datetime.now(UTC).isoformat(),
        "duration_seconds": 0.0, "calls_attempted": 0, "calls_succeeded": 0, "token_usage": None,
    }
    reason = unavailable_reason or "Adjudication did not complete."
    status = "unavailable"
    result = not_adjudicated(issues, reason)
    if unavailable_reason is None:
        try:
            provider, model, url, headers = gateway_config()
            metadata.update(provider=provider, model=model)
            # Strip the machine-local source path, without mutating native evidence.
            evidence_report = dict(report)
            evidence_report["skill"] = {k: v for k, v in report.get("skill", {}).items() if k != "source"}
            content = skill_file.read_text(encoding="utf-8")
            evidence = {
                "report": evidence_report, "issue_indices": list(range(1, len(issues) + 1)),
                "skill_text_with_line_numbers": "\n".join(
                    f"{index}: {line}" for index, line in enumerate(content.splitlines(), 1)
                ),
            }
            prompt = files("skill_assessment").joinpath("prompts/adjudicate.md").read_text(encoding="utf-8")
            payload = {
                "model": model, "messages": [{"role": "system", "content": prompt},
                                              {"role": "user", "content": json.dumps(evidence)}],
                "response_format": {"type": "json_object"}, "max_completion_tokens": 6000,
            }
            request = urllib.request.Request(url, data=json.dumps(payload).encode(), headers=headers)
            metadata["calls_attempted"] = 1
            with urllib.request.build_opener(NoRedirect()).open(request, timeout=timeout) as response:
                completion = json.load(response)
            metadata["calls_succeeded"] = 1
            metadata["response_model"] = completion.get("model")
            usage = completion.get("usage")
            if isinstance(usage, dict):
                metadata["token_usage"] = {key: usage[key] for key in (
                    "prompt_tokens", "completion_tokens", "total_tokens"
                ) if type(usage.get(key)) is int and usage[key] >= 0}
            choice = completion["choices"][0]
            if choice.get("finish_reason") != "stop":
                raise ValueError("Incomplete response")
            verdict = json.loads(choice["message"]["content"])
            validate_verdict(verdict, issues)
            result = verdict
            status = "completed"
        except ConfigurationUnavailable as exc:
            result = not_adjudicated(issues, str(exc))
        except urllib.error.HTTPError as exc:
            status = "failed"
            result = not_adjudicated(issues, f"Gateway returned HTTP {exc.code}; response body omitted.")
        except (OSError, ValueError, KeyError, IndexError, TypeError, AttributeError):
            status = "failed"
            result = not_adjudicated(issues, "Adjudication request, input, or response validation failed.")
    metadata["duration_seconds"] = round(time.monotonic() - started, 3)
    result.update(status=status, scope=SCOPE, metadata=metadata)
    try:
        with output.open("x", encoding="utf-8") as target:
            json.dump(result, target, indent=2)
            target.write("\n")
    except OSError as exc:
        raise OutputDirectoryError(f"Cannot save adjudication in {output.parent}") from exc
    return result
