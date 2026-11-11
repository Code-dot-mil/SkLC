"""Bounded SKILL.md adjudication through a configured chat-completions gateway."""

import json
import os
import time
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from datetime import UTC, datetime
from importlib.resources import files
from pathlib import Path
from urllib.parse import quote, urlencode, urlsplit

from .defaults import DEFAULT_MAX_COMPLETION_TOKENS, DEFAULT_TIMEOUT_SECONDS
from .errors import AdjudicationError, ConfigurationUnavailable, OutputDirectoryError

SCOPE = ("Reviews SKILL.md, scanner evidence, and requested skill files; "
         "unrequested files are not independently reviewed.")


@dataclass(frozen=True)
class GatewayConfig:
    """Connection settings for the selected adjudication gateway."""

    provider: str
    model: str
    url: str
    headers: dict[str, str] = field(repr=False)


def openai_config(model: str) -> GatewayConfig:
    base = os.environ.get("OPENAI_BASE_URL", "").strip() or "https://api.openai.com/v1"
    key = os.environ.get("OPENAI_API_KEY", "").strip()
    headers = {"Authorization": "Bearer " + key} if key else {}
    project = os.environ.get("OPENAI_PROJECT_ID", "").strip()
    if project:
        headers["OpenAI-Project"] = project
    return GatewayConfig(provider="openai", model=model, url=base.rstrip("/") + "/chat/completions", headers=headers)


def compatible_config(model: str) -> GatewayConfig:
    base = os.environ.get("SKILLSPECTOR_COMPAT_BASE_URL", "").strip()
    key = os.environ.get("SKILLSPECTOR_COMPAT_API_KEY", "").strip()
    return GatewayConfig(
        provider="openai_compatible", model=model,
        url=base.rstrip("/") + "/chat/completions" if base else "",
        headers={"Authorization": "Bearer " + key} if key else {},
    )


def azure_config(model: str) -> GatewayConfig:
    base = os.environ.get("AZURE_OPENAI_ENDPOINT", "").strip()
    key = os.environ.get("AZURE_OPENAI_API_KEY", "").strip()
    deployment = os.environ.get("AZURE_OPENAI_DEPLOYMENT", "").strip() or model
    version = os.environ.get("AZURE_OPENAI_API_VERSION", "").strip() or "2024-06-01"
    url = (base.rstrip("/") + "/openai/deployments/" + quote(deployment, safe="")
           + "/chat/completions?" + urlencode({"api-version": version})) if base else ""
    return GatewayConfig(provider="azure_openai", model=model, url=url, headers={"api-key": key} if key else {})


def gateway_config() -> GatewayConfig:
    """Reuse documented SkillSpector environment settings, without importing it."""
    provider = os.environ.get("SKILLSPECTOR_PROVIDER", "").strip().lower()
    model = os.environ.get("SKILLSPECTOR_MODEL", "").strip()
    factories = {"openai": openai_config, "openai_compatible": compatible_config, "azure_openai": azure_config}
    if provider not in factories:
        raise ConfigurationUnavailable("Adjudication requires openai, openai_compatible, or azure_openai provider.")
    config = factories[provider](model)
    if not (config.headers.get("Authorization") or config.headers.get("api-key")) or not config.url or not config.model:
        raise ConfigurationUnavailable("Adjudication requires an explicit model and the selected gateway credentials.")
    parsed = urlsplit(config.url)
    if parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password:
        raise ConfigurationUnavailable("Adjudication requires an HTTPS gateway without credentials in its URL.")
    config.headers["Content-Type"] = "application/json"
    return config


def validate_finding(verdict: object, issue: dict, index: int) -> None:
    """Check one finding against its position and identity in the native report."""
    if not isinstance(verdict, dict) or set(verdict) != {"index", "rule_id", "determination", "reason"}:
        raise ValueError("Unexpected finding fields")
    if (type(verdict["index"]) is not int or verdict["index"] != index
            or verdict["rule_id"] != issue.get("id", issue.get("rule_id"))):
        raise ValueError("Finding identity mismatch")
    if verdict["determination"] not in {"true_positive", "false_positive", "uncertain"}:
        raise ValueError("Unknown determination")
    if not isinstance(verdict["reason"], str) or not verdict["reason"].strip():
        raise ValueError("Missing finding rationale")


def validate_verdict(result: object, issues: list[dict], *, start_index: int = 1) -> None:
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
    for index, (verdict, issue) in enumerate(zip(verdicts, issues, strict=True), start_index):
        validate_finding(verdict, issue, index)
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


def build_evidence(report: dict, skill_file: Path) -> dict:
    """Strip the source path without mutating native evidence."""
    evidence_report = dict(report)
    evidence_report["skill"] = {k: v for k, v in report.get("skill", {}).items() if k != "source"}
    evidence_report["metadata"] = {k: v for k, v in report.get("metadata", {}).items() if k != "inference_usage"}
    content = skill_file.read_text(encoding="utf-8")
    return {
        "file_inventory": sorted(p.relative_to(skill_file.parent).as_posix()
                                 for p in skill_file.parent.rglob("*") if p.is_file() and not p.is_symlink()),
        "report": evidence_report, "issue_indices": list(range(1, len(report.get("issues", [])) + 1)),
        "skill_text_with_line_numbers": "\n".join(
            f"{index}: {line}" for index, line in enumerate(content.splitlines(), 1)
        ),
    }


@dataclass(frozen=True)
class GatewayResponse:
    """A received completion with inference metadata, before verdict validation."""

    completion: dict
    response_model: str | None
    token_usage: dict[str, int] | None

    def verdict(self) -> dict:
        choice = self.completion["choices"][0]
        if choice.get("finish_reason") == "length":
            raise AdjudicationError("Model output token limit reached.")
        if choice.get("finish_reason") != "stop":
            raise AdjudicationError("Model response did not finish normally.")
        try:
            return json.loads(choice["message"]["content"])
        except json.JSONDecodeError as exc:
            raise AdjudicationError("Model returned invalid JSON.") from exc


def request_completion(config: GatewayConfig, messages: list[dict], metadata: dict, *, timeout: int,
                       max_completion_tokens: int = DEFAULT_MAX_COMPLETION_TOKENS) -> GatewayResponse:
    """Request a completion while tracking attempts even when the gateway fails."""
    payload = {
        "model": config.model, "messages": messages,
        "response_format": {"type": "json_object"}, "max_completion_tokens": max_completion_tokens,
    }
    effort = os.environ.get("SKILLSPECTOR_REASONING_EFFORT", "").strip()
    if effort:
        payload["reasoning_effort"] = effort
    metadata.update(max_completion_tokens=max_completion_tokens, reasoning_effort=effort or None)
    request = urllib.request.Request(config.url, data=json.dumps(payload).encode(), headers=config.headers)
    metadata["calls_attempted"] += 1
    with urllib.request.build_opener(NoRedirect()).open(request, timeout=timeout) as response:
        completion = json.load(response)
    metadata["calls_succeeded"] += 1
    model = completion.get("model")
    usage = completion.get("usage")
    token_usage = None
    if isinstance(usage, dict):
        token_usage = {key: usage[key] for key in (
            "prompt_tokens", "completion_tokens", "total_tokens"
        ) if type(usage.get(key)) is int and usage[key] >= 0}
    return GatewayResponse(completion=completion, response_model=model, token_usage=token_usage)


def inference_metadata(*, provider: str | None = None, model: str | None = None) -> dict:
    """Start inference metadata without implying any request has been made."""
    return {
        "provider": provider,
        "model": model,
        "response_model": None, "created_at": datetime.now(UTC).isoformat(),
        "duration_seconds": 0.0, "calls_attempted": 0, "calls_succeeded": 0, "token_usage": None,
    }


def save_adjudication(result: dict, output: Path) -> dict:
    """Retain the adjudication artifact without overwriting an existing result."""
    try:
        with output.open("x", encoding="utf-8") as target:
            json.dump(result, target, indent=2)
            target.write("\n")
    except OSError as exc:
        raise OutputDirectoryError(f"Cannot save adjudication in {output.parent}") from exc
    return result


def record_static_adjudication(report: dict, output: Path) -> dict:
    """Record unadjudicated findings without loading configuration or calling an LLM."""
    result = not_adjudicated(report.get("issues", []), "Static-only scan; adjudication was not requested.")
    result["coverage_reason"] = "Adjudication coverage was not assessed."
    result.update(status="not_performed", scope=SCOPE, metadata=inference_metadata())
    return save_adjudication(result, output)


def review_batch(config: GatewayConfig, evidence: dict, metadata: dict, skill_file: Path,
                 supplied: dict, *, timeout: int, max_completion_tokens: int) -> dict:
    """Review up to twenty findings, sharing requested files with later batches."""
    prompt = files("skill_assessment").joinpath("prompts/adjudicate.md").read_text(encoding="utf-8")
    evidence = dict(evidence, additional_files_with_line_numbers=dict(supplied))
    messages = [{"role": "system", "content": prompt},
                {"role": "user", "content": json.dumps(evidence)}]
    for turn in range(2):
        completion = request_completion(config, messages, metadata, timeout=timeout,
                                        max_completion_tokens=max_completion_tokens)
        previous, usage = metadata["token_usage"], completion.token_usage
        if metadata["calls_succeeded"] == 1:
            metadata["token_usage"] = usage
        else:
            metadata["token_usage"] = ({k: previous[k] + usage[k] for k in previous.keys() & usage.keys()}
                                       if previous is not None and usage is not None else None)
        metadata["response_model"] = completion.response_model
        verdict = completion.verdict()
        if isinstance(verdict, dict) and "request_files" in verdict:
            if turn:
                raise AdjudicationError("Only one additional-file request is allowed.")
            requested = verdict["request_files"]
            if (set(verdict) != {"request_files"} or not isinstance(requested, list) or not requested
                    or any(not isinstance(name, str) or name not in evidence["file_inventory"]
                           for name in requested)):
                raise AdjudicationError("Model requested files outside the skill inventory.")
            contents = {}
            for name in requested:
                path = skill_file.parent / name
                if path.is_symlink() or not path.resolve().is_relative_to(skill_file.parent):
                    raise AdjudicationError("Requested file is outside the skill directory.")
                try:
                    text = path.read_text(encoding="utf-8")
                except (OSError, UnicodeError) as exc:
                    raise AdjudicationError(f"Cannot read requested UTF-8 skill file: {name}") from exc
                contents[name] = "\n".join(f"{i}: {line}" for i, line in enumerate(text.splitlines(), 1))
            supplied.update(contents)
            metadata["supplied_files"] = sorted({"SKILL.md"} | supplied.keys())
            messages.extend([{"role": "assistant", "content": json.dumps(verdict)},
                             {"role": "user", "content": json.dumps({"files": contents,
                              "instruction": "Return the final adjudication; no further file requests."})}])
            continue
        try:
            validate_verdict(verdict, evidence["report"]["issues"],
                             start_index=evidence["issue_indices"][0] if evidence["issue_indices"] else 1)
        except ValueError as exc:
            raise AdjudicationError(str(exc)) from exc
        return verdict


def adjudicate_report(
    report: dict, skill_file: Path, output: Path, *, timeout: int = DEFAULT_TIMEOUT_SECONDS,
    static_only: bool = False, unavailable_reason: str | None = None,
    max_completion_tokens: int = DEFAULT_MAX_COMPLETION_TOKENS,
) -> dict:
    """Save a verdict or explicit non-adjudication, leaving the raw report unchanged."""
    if static_only:
        return record_static_adjudication(report, output)
    started = time.monotonic()
    issues = report.get("issues", [])
    metadata = inference_metadata(
        provider=os.environ.get("SKILLSPECTOR_PROVIDER", "").strip().lower() or None,
        model=os.environ.get("SKILLSPECTOR_MODEL", "").strip() or None,
    )
    reason = unavailable_reason or "Adjudication did not complete."
    status = "unavailable"
    result = not_adjudicated(issues, reason)
    verdicts = []
    if unavailable_reason is None:
        try:
            config = gateway_config()
            metadata.update(provider=config.provider, model=config.model)
            skill_file = skill_file.parent.resolve() / skill_file.name
            if skill_file.is_symlink():
                raise AdjudicationError("SKILL.md must be a regular file in the skill directory.")
            evidence = build_evidence(report, skill_file)
            metadata.update(supplied_files=["SKILL.md"], batch_size=20,
                            batches_total=max(1, (len(issues) + 19) // 20), batches_completed=0)
            supplied = {}
            for start in range(0, max(1, len(issues)), 20):
                selected = issues[start:start + 20]
                batch = dict(evidence, report=dict(evidence["report"], issues=selected),
                             issue_indices=list(range(start + 1, start + len(selected) + 1)))
                verdicts.append(review_batch(config, batch, metadata, skill_file, supplied,
                                             timeout=timeout, max_completion_tokens=max_completion_tokens))
                metadata["batches_completed"] = len(verdicts)
            result = {
                "safe_to_use": all(v["safe_to_use"] for v in verdicts),
                "summary": "\n".join(dict.fromkeys(v["summary"] for v in verdicts)),
                "coverage_sufficient": all(v["coverage_sufficient"] for v in verdicts),
                "coverage_reason": "\n".join(dict.fromkeys(v["coverage_reason"] for v in verdicts)),
                "findings": [finding for verdict in verdicts for finding in verdict["findings"]],
            }
            validate_verdict(result, issues)
            status = "completed"
        except ConfigurationUnavailable as exc:
            result = not_adjudicated(issues, str(exc))
        except urllib.error.HTTPError as exc:
            status = "failed"
            result = not_adjudicated(issues, f"Gateway returned HTTP {exc.code}; response body omitted.")
        except AdjudicationError as exc:
            status = "failed"
            result = not_adjudicated(issues, str(exc))
        except TimeoutError:
            status = "failed"
            result = not_adjudicated(issues, "Adjudication request timed out.")
        except (OSError, ValueError, KeyError, IndexError, TypeError, AttributeError):
            status = "failed"
            result = not_adjudicated(issues, "Adjudication request, input, or response validation failed.")
    if status != "completed":
        for verdict in verdicts:
            for finding in verdict["findings"]:
                result["findings"][finding["index"] - 1] = finding
    metadata["duration_seconds"] = round(time.monotonic() - started, 3)
    result.update(status=status, scope=SCOPE, metadata=metadata)
    return save_adjudication(result, output)
