"""Provider abstraction: the interface every LLM backend implements.

An ``AgentProvider`` turns a (role, system_prompt, payload, schema) request
into a validated Pydantic model instance. Providers know how to talk to a
specific backend (Anthropic, Gemini, OpenRouter, Ollama, or the offline
mock); they know nothing about committee ordering, the risk veto, or
persistence -- that lives in ``agents.committee`` and the API layer.

No provider may be silently substituted for another: manual selection of an
unconfigured or unreachable provider raises ``ProviderNotConfiguredError``
rather than falling back to the mock.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import ClassVar, TypeVar

from pydantic import BaseModel

from agents.roles import AgentRole

SchemaT = TypeVar("SchemaT", bound=BaseModel)


class ProviderError(Exception):
    """Base class for all provider failures."""


class ProviderNotConfiguredError(ProviderError):
    """Raised when a manually selected provider is not usable.

    Covers both missing configuration (e.g. an unset API key env var) and,
    for Ollama specifically, an unreachable local server. The message should
    always name the missing env var or unreachable URL so the caller can fix
    it without reading source code.
    """


class ProviderResponseError(ProviderError):
    """Raised when a provider returned output that could not be validated.

    Covers malformed JSON, JSON that fails schema validation, and any other
    "the provider responded but we can't trust the response" case.
    """


class AgentProvider(ABC):
    """Interface every LLM backend (and the offline mock) implements.

    Attributes:
        name: Short identifier used in the provider registry and reported to
            callers as ``selected_provider`` (e.g. "anthropic", "mock").
    """

    name: ClassVar[str]

    @classmethod
    @abstractmethod
    def is_configured(cls) -> bool:
        """Return True if this provider can plausibly be used right now.

        This is a configuration-presence check (env vars set), NOT a network
        call -- with the sole documented exception of Ollama, which performs
        a fast local reachability probe because "configured" for a local
        server means "running and reachable."
        """
        raise NotImplementedError

    @classmethod
    def not_configured_reason(cls) -> str:
        """Human-readable reason this provider is not currently usable.

        Used by ``agents.providers.registry.get_provider`` to build a
        ``ProviderNotConfiguredError`` message that names the specific
        missing env var (or unreachable URL, for Ollama) rather than a
        generic "not configured". Subclasses should override this.
        """
        return f"provider {cls.name!r} is not configured"

    @abstractmethod
    def generate(
        self,
        role: AgentRole,
        system_prompt: str,
        payload: dict,
        schema: type[SchemaT],
    ) -> SchemaT:
        """Generate and validate one committee agent's output.

        Args:
            role: Which committee role is being generated (for backends that
                want to tailor request shape/logging per role).
            system_prompt: The role's system prompt (see
                ``agents.committee.SYSTEM_PROMPTS``).
            payload: JSON-safe dict of deterministic context for this role
                (see ``agents.committee.build_agent_payload``).
            schema: The Pydantic model the response must validate against.

        Returns:
            A validated instance of ``schema``.

        Raises:
            ProviderNotConfiguredError: The provider is not usable (only
                relevant for manual selection; ``get_provider`` raises this
                eagerly at selection time in the common case).
            ProviderResponseError: The provider responded but the response
                could not be validated against ``schema``.
            ProviderError: Any other provider-side failure (network, auth,
                refusal, etc.).
        """
        raise NotImplementedError
