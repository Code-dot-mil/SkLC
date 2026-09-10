from __future__ import annotations

import os
import re
from typing import Any

_HTTP_HEADER_NAME = re.compile(r"^[!#$%&'*+.^_`|~0-9A-Za-z-]+$")


def configure_openai_compatible_provider() -> None:
    header_name = os.environ.get("SKILL_EXCHANGE_LLM_API_KEY_HEADER", "").strip()
    requests_per_second_value = os.environ.get("SKILL_EXCHANGE_LLM_REQUESTS_PER_SECOND", "").strip()
    if not header_name and not requests_per_second_value:
        return
    if header_name and not _HTTP_HEADER_NAME.fullmatch(header_name):
        raise RuntimeError("SKILL_EXCHANGE_LLM_API_KEY_HEADER must be a valid HTTP header name")
    if os.environ.get("SKILLSPECTOR_PROVIDER", "").strip() != "openai_compatible":
        raise RuntimeError("gateway header and rate settings require the openai_compatible provider")

    api_key = os.environ.get("SKILLSPECTOR_COMPAT_API_KEY", "").strip()
    if not api_key:
        raise RuntimeError("gateway header and rate settings require SKILL_EXCHANGE_LLM_API_KEY")

    rate_limiter = None
    if requests_per_second_value:
        try:
            requests_per_second = float(requests_per_second_value)
        except ValueError as error:
            raise RuntimeError("SKILL_EXCHANGE_LLM_REQUESTS_PER_SECOND must be a number") from error
        if requests_per_second <= 0:
            raise RuntimeError("SKILL_EXCHANGE_LLM_REQUESTS_PER_SECOND must be greater than zero")
        from langchain_core.rate_limiters import InMemoryRateLimiter

        rate_limiter = InMemoryRateLimiter(requests_per_second=requests_per_second, max_bucket_size=1)

    from skillspector.providers.chat_models import create_openai_compatible_chat_model
    from skillspector.providers.openai_compatible.provider import OpenAICompatibleProvider

    def create_chat_model(
        self: Any,
        model: str,
        *,
        max_tokens: int,
        timeout: float | None = 120,
    ) -> Any:
        chat_model = create_openai_compatible_chat_model(
            model=model,
            credentials=self.resolve_credentials(),
            max_tokens=max_tokens,
            timeout=timeout,
            default_headers={header_name: api_key} if header_name else None,
        )
        if chat_model is not None and rate_limiter is not None:
            chat_model.rate_limiter = rate_limiter
        return chat_model

    OpenAICompatibleProvider.create_chat_model = create_chat_model


def main() -> None:
    configure_openai_compatible_provider()
    from skillspector.cli import app

    app()


if __name__ == "__main__":
    main()
