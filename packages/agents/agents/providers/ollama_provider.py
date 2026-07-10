"""Local Ollama provider, via a direct ``httpx`` call to its chat API.

Ollama has no API key: "configured" means "a server is actually reachable."
This is the one documented exception to the "no network in ``is_configured``"
rule -- a fast (1.5s timeout) probe against ``{base}/api/tags`` is used both
to auto-detect a locally running Ollama in AUTO mode and to fail fast with a
helpful message when Ollama is selected manually but not reachable.
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

DEFAULT_MODEL = "llama3.2"
DEFAULT_BASE_URL = "http://localhost:11434"
PROBE_TIMEOUT_SECONDS = 1.5
REQUEST_TIMEOUT_SECONDS = 30.0


def _resolve_base_url() -> str:
    return os.getenv("OLLAMA_BASE_URL", DEFAULT_BASE_URL).rstrip("/")


class OllamaAgentProvider(AgentProvider):
    """Committee provider backed by a local Ollama server's chat API."""

    name: ClassVar[str] = "ollama"

    def __init__(self, model: str | None = None, base_url: str | None = None) -> None:
        self._model = model or os.getenv("OLLAMA_MODEL", DEFAULT_MODEL)
        self._base_url = base_url or _resolve_base_url()

    @staticmethod
    def _probe(base_url: str) -> bool:
        """Fast reachability check; any exception at all means "not reachable"."""
        try:
            response = httpx.get(f"{base_url}/api/tags", timeout=PROBE_TIMEOUT_SECONDS)
            return response.status_code < 500
        except Exception:
            return False

    @classmethod
    def is_configured(cls) -> bool:
        """True if a local Ollama server responds at the resolved base URL.

        Resolves the base URL from ``OLLAMA_BASE_URL`` (default
        ``http://localhost:11434``) and probes ``{base}/api/tags``. This is
        the one provider where "configured" requires a network round trip,
        because there is no credential whose mere presence would indicate
        usability -- probing is how auto mode decides whether to include a
        local model.
        """
        return cls._probe(_resolve_base_url())

    @classmethod
    def not_configured_reason(cls) -> str:
        base = _resolve_base_url()
        return f"Ollama not reachable at {base}; is it running?"

    def generate(
        self,
        role: AgentRole,
        system_prompt: str,
        payload: dict,
        schema: type[BaseModel],
    ) -> BaseModel:
        if not self._probe(self._base_url):
            raise ProviderNotConfiguredError(
                f"Ollama not reachable at {self._base_url}; is it running?"
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
            "format": "json",
            "stream": False,
        }

        try:
            response = httpx.post(
                f"{self._base_url}/api/chat", json=body, timeout=REQUEST_TIMEOUT_SECONDS
            )
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            raise ProviderError(
                f"Ollama returned an error (status={exc.response.status_code}): {exc}"
            ) from exc
        except httpx.HTTPError as exc:
            raise ProviderError(f"Could not reach Ollama at {self._base_url}: {exc}") from exc

        try:
            data = response.json()
            content = data["message"]["content"]
            parsed = json.loads(content)
        except (KeyError, json.JSONDecodeError, ValueError) as exc:
            raise ProviderResponseError(
                f"Ollama response could not be parsed as the expected JSON shape: {exc}"
            ) from exc

        try:
            return schema.model_validate(parsed)
        except ValidationError as exc:
            raise ProviderResponseError(f"Ollama response failed schema validation: {exc}") from exc
