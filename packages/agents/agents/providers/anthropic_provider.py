"""Anthropic Claude provider, using the official ``anthropic`` Python SDK.

Never issues raw HTTP: all requests go through ``anthropic.Anthropic`` and its
structured-output helper (``messages.parse``), which validates the response
against a Pydantic schema for us and hands back ``response.parsed_output``.

The SDK is imported lazily (inside ``generate``/client construction) so that
importing this module -- and the whole ``agents`` package -- never requires
the ``anthropic`` dependency to be installed with a usable environment; it
only needs to be importable when this provider is actually selected.
"""

from __future__ import annotations

import json
import os
from typing import ClassVar

from pydantic import BaseModel

from agents.providers.base import (
    AgentProvider,
    ProviderError,
    ProviderNotConfiguredError,
    ProviderResponseError,
)
from agents.roles import AgentRole

DEFAULT_MODEL = "claude-opus-4-8"


class AnthropicAgentProvider(AgentProvider):
    """Committee provider backed by the Anthropic Messages API."""

    name: ClassVar[str] = "anthropic"

    def __init__(self, model: str | None = None) -> None:
        self._model = model or os.getenv("ANTHROPIC_MODEL", DEFAULT_MODEL)

    @classmethod
    def is_configured(cls) -> bool:
        """True if ``ANTHROPIC_API_KEY`` is set. No network call."""
        return bool(os.getenv("ANTHROPIC_API_KEY"))

    @classmethod
    def not_configured_reason(cls) -> str:
        return "ANTHROPIC_API_KEY is not set"

    def generate(
        self,
        role: AgentRole,
        system_prompt: str,
        payload: dict,
        schema: type[BaseModel],
    ) -> BaseModel:
        if not self.is_configured():
            raise ProviderNotConfiguredError(
                "Anthropic provider selected but ANTHROPIC_API_KEY is not set."
            )

        try:
            import anthropic
        except ImportError as exc:  # pragma: no cover - exercised only if SDK missing
            raise ImportError(
                "The 'anthropic' package is required to use the Anthropic provider. "
                "Install it with `pip install anthropic`."
            ) from exc

        client = anthropic.Anthropic()  # reads ANTHROPIC_API_KEY from the environment

        try:
            response = client.messages.parse(
                model=self._model,
                max_tokens=4096,
                system=system_prompt,
                messages=[{"role": "user", "content": json.dumps(payload, default=str)}],
                output_format=schema,
            )
        except anthropic.AuthenticationError as exc:
            raise ProviderNotConfiguredError(
                f"Anthropic rejected the API key (authentication error): {exc}"
            ) from exc
        except anthropic.APIConnectionError as exc:
            raise ProviderError(f"Could not reach the Anthropic API: {exc}") from exc
        except anthropic.APIStatusError as exc:
            raise ProviderError(
                f"Anthropic API returned an error (status={exc.status_code}): {exc}"
            ) from exc

        if response.stop_reason == "refusal":
            raise ProviderError("Anthropic declined the request (refusal stop reason).")

        result = response.parsed_output
        if result is None:
            raise ProviderResponseError(
                "Anthropic response could not be parsed into the required schema."
            )
        return result
