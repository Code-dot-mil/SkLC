from __future__ import annotations

import json
import os
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path

from .errors import AssessmentError

DEFAULT_SCAN_MODE = "llm-assisted"
DEFAULT_TIMEOUT_SECONDS = 600
SUPPORTED_ASSESSOR = "skillspector"
SUPPORTED_SCAN_MODES = {"llm-assisted", "static-only"}


@dataclass(frozen=True)
class SkillSpectorConfig:
    scan_mode: str
    timeout_seconds: int
    llm_provider: str | None = None
    llm_api_key: str | None = None
    llm_base_url: str | None = None
    llm_model: str | None = None


def _load_config(path: Path | None) -> dict[str, object]:
    if path is None:
        return {}
    try:
        parsed = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise AssessmentError(f"cannot read assessment configuration {path}: {exc}") from exc
    if not isinstance(parsed, dict) or set(parsed) - {"assessors"}:
        raise AssessmentError("configuration must be an object containing only 'assessors'")
    assessors = parsed.get("assessors", {})
    if not isinstance(assessors, dict) or set(assessors) - {SUPPORTED_ASSESSOR}:
        raise AssessmentError("configuration contains an unsupported assessor")
    settings = assessors.get(SUPPORTED_ASSESSOR, {})
    if not isinstance(settings, dict) or set(settings) - {"scan_mode", "timeout_seconds"}:
        raise AssessmentError("configuration contains an unsupported skillspector setting")
    return settings


def _positive_int(value: object, setting: str) -> int:
    if isinstance(value, bool) or not isinstance(value, (int, str)):
        raise AssessmentError(f"{setting} must be a positive integer")
    try:
        parsed = int(value)  # type: ignore[arg-type]
    except (TypeError, ValueError) as exc:
        raise AssessmentError(f"{setting} must be a positive integer") from exc
    if parsed <= 0 or str(parsed) != str(value).strip():
        raise AssessmentError(f"{setting} must be a positive integer")
    return parsed


def load_skillspector_config(
    path: Path | None,
    environ: Mapping[str, str] | None = None,
    *,
    require_llm_values: bool = True,
) -> SkillSpectorConfig:
    env = os.environ if environ is None else environ
    settings = _load_config(path)
    scan_mode = env.get("SKLC_SKILLSPECTOR_SCAN_MODE", str(settings.get("scan_mode", DEFAULT_SCAN_MODE))).strip()
    if scan_mode not in SUPPORTED_SCAN_MODES:
        raise AssessmentError(f"unsupported SkillSpector scan mode: {scan_mode}")
    timeout_raw: object = env.get(
        "SKLC_SKILLSPECTOR_TIMEOUT_SECONDS", settings.get("timeout_seconds", DEFAULT_TIMEOUT_SECONDS)
    )
    timeout_seconds = _positive_int(timeout_raw, "SkillSpector timeout_seconds")

    if scan_mode == "static-only":
        return SkillSpectorConfig(scan_mode=scan_mode, timeout_seconds=timeout_seconds)

    names = {
        "llm_provider": "SKLC_LLM_PROVIDER",
        "llm_api_key": "SKLC_LLM_API_KEY",
        "llm_base_url": "SKLC_LLM_BASE_URL",
        "llm_model": "SKLC_LLM_MODEL",
    }
    values = {field: env.get(variable, "").strip() for field, variable in names.items()}
    if values["llm_provider"] and values["llm_provider"] != "openai_compatible":
        raise AssessmentError("SKLC_LLM_PROVIDER must be openai_compatible")
    if require_llm_values:
        missing = [variable for field, variable in names.items() if not values[field]]
        if missing:
            raise AssessmentError(f"llm-assisted mode requires: {', '.join(missing)}")
    return SkillSpectorConfig(scan_mode=scan_mode, timeout_seconds=timeout_seconds, **values)


def validate_assessors(assessors: list[str]) -> list[str]:
    if not assessors:
        raise AssessmentError("at least one --assessor is required")
    unknown = sorted(set(assessors) - {SUPPORTED_ASSESSOR})
    if unknown:
        raise AssessmentError(f"unsupported assessor: {', '.join(unknown)}")
    if len(assessors) != len(set(assessors)):
        raise AssessmentError("duplicate --assessor values are not allowed")
    return sorted(assessors)
