"""LLM provider abstraction for the QuantCouncil AI committee.

Public surface:
    ``AgentProvider``: the interface every backend implements.
    ``ProviderError`` / ``ProviderNotConfiguredError`` / ``ProviderResponseError``:
        the provider exception hierarchy.
    ``MockAgentProvider``: offline, deterministic, keyless default.
    ``AnthropicAgentProvider`` / ``GeminiAgentProvider`` /
    ``OpenRouterAgentProvider`` / ``OllamaAgentProvider``: real backends.
    ``get_provider`` / ``resolve_auto`` / ``PROVIDER_CLASSES`` / ``AUTO_PRIORITY``:
        selection.
"""

from __future__ import annotations

from agents.providers.anthropic_provider import AnthropicAgentProvider
from agents.providers.base import (
    AgentProvider,
    ProviderError,
    ProviderNotConfiguredError,
    ProviderResponseError,
)
from agents.providers.gemini_provider import GeminiAgentProvider
from agents.providers.mock import MockAgentProvider
from agents.providers.ollama_provider import OllamaAgentProvider
from agents.providers.openrouter_provider import OpenRouterAgentProvider
from agents.providers.registry import AUTO_PRIORITY, PROVIDER_CLASSES, get_provider, resolve_auto

__all__ = [
    "AgentProvider",
    "ProviderError",
    "ProviderNotConfiguredError",
    "ProviderResponseError",
    "MockAgentProvider",
    "AnthropicAgentProvider",
    "GeminiAgentProvider",
    "OpenRouterAgentProvider",
    "OllamaAgentProvider",
    "PROVIDER_CLASSES",
    "AUTO_PRIORITY",
    "get_provider",
    "resolve_auto",
]
