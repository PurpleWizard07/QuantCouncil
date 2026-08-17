"""Google Gemini provider, via a direct ``httpx`` call to the REST API.

Uses the ``generateContent`` endpoint with ``response_mime_type:
application/json`` to request JSON output, then validates the returned text
against the requested Pydantic schema. Gemini's REST API does not accept a
Pydantic model directly, so the schema's JSON structure is described in the
prompt text as a strong hint; validation is what actually enforces it.
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

DEFAULT_MODEL = "gemini-2.0-flash"
API_BASE = "https://generativelanguage.googleapis.com/v1beta/models"
TIMEOUT_SECONDS = 30.0


class GeminiAgentProvider(AgentProvider):
    """Committee provider backed by the Gemini ``generateContent`` REST API."""

    name: ClassVar[str] = "gemini"

    def __init__(self, model: str | None = None) -> None:
        self._model = model or os.getenv("GEMINI_MODEL", DEFAULT_MODEL)

    @classmethod
    def is_configured(cls) -> bool:
        """True if ``GEMINI_API_KEY`` is set. No network call."""
        return bool(os.getenv("GEMINI_API_KEY"))

    @classmethod
    def not_configured_reason(cls) -> str:
        return "GEMINI_API_KEY is not set"

    def generate(
        self,
        role: AgentRole,
        system_prompt: str,
        payload: dict,
        schema: type[BaseModel],
    ) -> BaseModel:
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise ProviderNotConfiguredError(
                "Gemini provider selected but GEMINI_API_KEY is not set."
            )

        # NOTE: this embeds the API key as a query parameter, per Gemini's
        # REST API. Never log this URL or let an exception whose message
        # includes it (e.g. httpx.HTTPStatusError) propagate unsanitized --
        # see the sanitized exception handling below.
        url = f"{API_BASE}/{self._model}:generateContent?key={api_key}"
        user_content = (
            f"{json.dumps(payload, default=str)}\n\n"
            "Respond with a single JSON object matching this schema (JSON Schema):\n"
            f"{json.dumps(schema.model_json_schema())}"
        )
        body = {
            "system_instruction": {"parts": [{"text": system_prompt}]},
            "contents": [{"role": "user", "parts": [{"text": user_content}]}],
            "generationConfig": {"response_mime_type": "application/json"},
        }

        try:
            response = httpx.post(url, json=body, timeout=TIMEOUT_SECONDS)
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            # NEVER interpolate `exc` (or its `.request`/`.response`) here:
            # ``url`` embeds GEMINI_API_KEY as a query parameter, and
            # httpx's HTTPStatusError message includes ``str(request.url)``
            # verbatim (query strings are not redacted, only userinfo is).
            # A static, status-only message is the only safe option -- the
            # full exception is still chained via ``from exc`` and preserved
            # in the server-side traceback for anyone who calls
            # ``logger.exception``.
            raise ProviderError(
                f"Gemini API returned an error (status={exc.response.status_code})."
            ) from exc
        except httpx.HTTPError as exc:
            # Same reasoning: network/timeout errors can also carry the
            # request (and therefore the API key) in their message.
            raise ProviderError("Could not reach the Gemini API.") from exc

        try:
            data = response.json()
            text = data["candidates"][0]["content"]["parts"][0]["text"]
            parsed = json.loads(text)
        except (KeyError, IndexError, json.JSONDecodeError, ValueError) as exc:
            raise ProviderResponseError(
                "Gemini response could not be parsed as the expected JSON shape."
            ) from exc

        try:
            return schema.model_validate(parsed)
        except ValidationError as exc:
            raise ProviderResponseError(
                "Gemini response failed schema validation."
            ) from exc
