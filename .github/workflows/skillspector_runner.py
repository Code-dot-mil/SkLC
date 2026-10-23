"""Pinned upstream CI adapter for the configured gateway; not part of assessment-kit."""

from __future__ import annotations

import math
import os
import re
from typing import Any


def configure_openai_compatible_provider() -> None:
    from langchain_core.rate_limiters import InMemoryRateLimiter
    from skillspector.providers.chat_models import create_openai_compatible_chat_model
    from skillspector.providers.openai_compatible.provider import OpenAICompatibleProvider

    header_name = os.environ["LLM_API_KEY_HEADER"].strip()
    api_key = os.environ["SKILLSPECTOR_COMPAT_API_KEY"].strip()
    if not re.fullmatch(r"[!#$%&'*+.^_`|~0-9A-Za-z-]+", header_name):
        raise RuntimeError("LLM_API_KEY_HEADER must be a valid HTTP header name")
    if os.environ["SKILLSPECTOR_PROVIDER"] != "openai_compatible" or not api_key:
        raise RuntimeError("Gateway adapter requires openai_compatible and its API key")
    max_output_tokens = int(os.environ["LLM_MAX_OUTPUT_TOKENS"])
    requests_per_second = float(os.environ["LLM_REQUESTS_PER_SECOND"])
    if max_output_tokens <= 0 or not math.isfinite(requests_per_second) or requests_per_second <= 0:
        raise RuntimeError("Gateway token limit and request rate must be positive finite values")
    rate_limiter = InMemoryRateLimiter(requests_per_second=requests_per_second, max_bucket_size=1)
    original_get_max_output_tokens = OpenAICompatibleProvider.get_max_output_tokens

    def get_max_output_tokens(self: Any, model: str) -> int:
        discovered_limit = original_get_max_output_tokens(self, model)
        return min(discovered_limit, max_output_tokens) if discovered_limit is not None else max_output_tokens

    def create_chat_model(
        self: Any, model: str, *, max_tokens: int, timeout: float | None = 120,
    ) -> Any:
        chat_model = create_openai_compatible_chat_model(
            model=model, credentials=self.resolve_credentials(),
            max_tokens=min(max_tokens, max_output_tokens), timeout=timeout,
            default_headers={header_name: api_key},
        )
        if chat_model is not None:
            chat_model.rate_limiter = rate_limiter
        return chat_model

    OpenAICompatibleProvider.create_chat_model = create_chat_model
    OpenAICompatibleProvider.get_max_output_tokens = get_max_output_tokens


def configure_scan_budget() -> None:
    from skillspector import cli
    from skillspector.state import WorkflowResourceBudget

    scan_max_seconds = int(os.environ["ASSESSMENT_TIMEOUT_SECONDS"])
    if scan_max_seconds <= 0:
        raise RuntimeError("ASSESSMENT_TIMEOUT_SECONDS must be positive")
    original_scan_state = cli._scan_state

    def scan_state(*args: Any, **kwargs: Any) -> dict[str, object]:
        state = original_scan_state(*args, **kwargs)
        state["workflow_resource_budget"] = WorkflowResourceBudget(max_seconds=scan_max_seconds)
        return state

    cli._scan_state = scan_state


def main() -> None:
    configure_openai_compatible_provider()
    from skillspector.cli import app

    configure_scan_budget()
    app()


if __name__ == "__main__":
    main()
