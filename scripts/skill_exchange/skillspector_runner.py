from __future__ import annotations

import os
import re
from typing import Any

_HTTP_HEADER_NAME = re.compile(r"^[!#$%&'*+.^_`|~0-9A-Za-z-]+$")


def configure_api_key_header() -> None:
    header_name = os.environ.get("SKILL_EXCHANGE_LLM_API_KEY_HEADER", "").strip()
    if not header_name:
        return
    if not _HTTP_HEADER_NAME.fullmatch(header_name):
        raise RuntimeError("SKILL_EXCHANGE_LLM_API_KEY_HEADER must be a valid HTTP header name")
    if os.environ.get("SKILLSPECTOR_PROVIDER", "").strip() != "openai_compatible":
        raise RuntimeError("SKILL_EXCHANGE_LLM_API_KEY_HEADER requires the openai_compatible provider")

    api_key = os.environ.get("SKILLSPECTOR_COMPAT_API_KEY", "").strip()
    if not api_key:
        raise RuntimeError("SKILL_EXCHANGE_LLM_API_KEY_HEADER requires SKILL_EXCHANGE_LLM_API_KEY")

    from skillspector.providers.chat_models import create_openai_compatible_chat_model
    from skillspector.providers.openai_compatible.provider import OpenAICompatibleProvider

    def create_chat_model(
        self: Any,
        model: str,
        *,
        max_tokens: int,
        timeout: float | None = 120,
    ) -> Any:
        return create_openai_compatible_chat_model(
            model=model,
            credentials=self.resolve_credentials(),
            max_tokens=max_tokens,
            timeout=timeout,
            default_headers={header_name: api_key},
        )

    OpenAICompatibleProvider.create_chat_model = create_chat_model


def main() -> None:
    configure_api_key_header()
    from skillspector.cli import app

    app()


if __name__ == "__main__":
    main()
