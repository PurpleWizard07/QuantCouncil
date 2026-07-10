"""OpenRouter provider, via a direct ``httpx`` call to its chat completions API.

OpenRouter proxies many underlying models behind an OpenAI-compatible chat
completions endpoint. The default model is a ``:free``-tier model; note that
``:free`` model availability, rate limits, and quality vary by provider and
account and are outside this package's control -- set ``OPENROUTER_MODEL`` to
pin a specific (paid) model if the free tier is not suitable.
"""

from __future__ import annotations

import json
import os
from typing import ClassVar

import httpx
from pydantic import BaseModel, ValidationError

from agents.providers.base import (
    AgentProvider,
    ProviderError,
    ProviderNotConfiguredError,
    ProviderResponseError,
)
from agents.roles import AgentRole

DEFAULT_MODEL = "meta-llama/llama-3.3-70b-instruct:free"
API_URL = "https://openrouter.ai/api/v1/chat/completions"
TIMEOUT_SECONDS = 30.0


class OpenRouterAgentProvider(AgentProvider):
    """Committee provider backed by the OpenRouter chat completions API."""

    name: ClassVar[str] = "openrouter"

    def __init__(self, model: str | None = None) -> None:
        self._model = model or os.getenv("OPENROUTER_MODEL", DEFAULT_MODEL)

    @classmethod
    def is_configured(cls) -> bool:
        """True if ``OPENROUTER_API_KEY`` is set. No network call."""
        return bool(os.getenv("OPENROUTER_API_KEY"))

    @classmethod
    def not_configured_reason(cls) -> str:
        return "OPENROUTER_API_KEY is not set"

    def generate(
        self,
        role: AgentRole,
        system_prompt: str,
        payload: dict,
        schema: type[BaseModel],
    ) -> BaseModel:
        api_key = os.getenv("OPENROUTER_API_KEY")
        if not api_key:
            raise ProviderNotConfiguredError(
                "OpenRouter provider selected but OPENROUTER_API_KEY is not set."
            )

        user_content = (
            f"{json.dumps(payload, default=str)}\n\n"
            "Respond with a single JSON object matching this schema (JSON Schema):\n"
            f"{json.dumps(schema.model_json_schema())}"
        )
        body = {
            "model": self._model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_content},
            ],
            "response_format": {"type": "json_object"},
        }
        headers = {"Authorization": f"Bearer {api_key}"}

        try:
            response = httpx.post(API_URL, json=body, headers=headers, timeout=TIMEOUT_SECONDS)
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            raise ProviderError(
                f"OpenRouter API returned an error (status={exc.response.status_code}): {exc}"
            ) from exc
        except httpx.HTTPError as exc:
            raise ProviderError(f"Could not reach the OpenRouter API: {exc}") from exc

        try:
            data = response.json()
            content = data["choices"][0]["message"]["content"]
            parsed = json.loads(content)
        except (KeyError, IndexError, json.JSONDecodeError, ValueError) as exc:
            raise ProviderResponseError(
                f"OpenRouter response could not be parsed as the expected JSON shape: {exc}"
            ) from exc

        try:
            return schema.model_validate(parsed)
        except ValidationError as exc:
            raise ProviderResponseError(
                f"OpenRouter response failed schema validation: {exc}"
            ) from exc
