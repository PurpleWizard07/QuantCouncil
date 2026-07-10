"""Provider selection: manual by name, or automatic priority-based resolution.

Manual selection is strict: choosing a provider by name that is not
configured (or, for Ollama, not reachable) raises
``ProviderNotConfiguredError`` immediately -- it never silently falls back to
the mock. Only ``"auto"`` walks the priority list and falls back, and even
``resolve_auto()`` can never fail outright because the mock is always
configured.
"""

from __future__ import annotations

from agents.providers.anthropic_provider import AnthropicAgentProvider
from agents.providers.base import AgentProvider, ProviderNotConfiguredError
from agents.providers.gemini_provider import GeminiAgentProvider
from agents.providers.mock import MockAgentProvider
from agents.providers.ollama_provider import OllamaAgentProvider
from agents.providers.openrouter_provider import OpenRouterAgentProvider

PROVIDER_CLASSES: dict[str, type[AgentProvider]] = {
    "mock": MockAgentProvider,
    "anthropic": AnthropicAgentProvider,
    "gemini": GeminiAgentProvider,
    "openrouter": OpenRouterAgentProvider,
    "ollama": OllamaAgentProvider,
}
"""Every known provider name, mapped to its implementation class."""

AUTO_PRIORITY: list[str] = ["anthropic", "gemini", "openrouter", "ollama", "mock"]
"""Order ``resolve_auto`` checks providers in. ``mock`` is always configured
and last, so auto-resolution always succeeds."""


def get_provider(name: str) -> AgentProvider:
    """Select a provider by name, or resolve one automatically.

    Args:
        name: A key in ``PROVIDER_CLASSES``, or ``"auto"`` to resolve the
            highest-priority configured provider (see ``AUTO_PRIORITY``).

    Returns:
        An instantiated, ready-to-use ``AgentProvider``.

    Raises:
        ValueError: ``name`` is not ``"auto"`` and not a known provider name.
        ProviderNotConfiguredError: ``name`` names a real (non-auto) provider
            that is not configured (or, for Ollama, not reachable). Manual
            selection never falls back to the mock.
    """
    if name == "auto":
        return resolve_auto()

    provider_class = PROVIDER_CLASSES.get(name)
    if provider_class is None:
        allowed = ", ".join(sorted({"auto", *PROVIDER_CLASSES}))
        raise ValueError(f"Unknown provider {name!r}. Allowed values: {allowed}.")

    if not provider_class.is_configured():
        raise ProviderNotConfiguredError(
            f"Provider {name!r} is not usable: {provider_class.not_configured_reason()}"
        )
    return provider_class()


def resolve_auto() -> AgentProvider:
    """Return the first configured provider in ``AUTO_PRIORITY`` order.

    Always succeeds: ``mock`` is always configured and is the last entry in
    ``AUTO_PRIORITY``.
    """
    for name in AUTO_PRIORITY:
        provider_class = PROVIDER_CLASSES[name]
        if provider_class.is_configured():
            return provider_class()
    # Unreachable in practice: mock.is_configured() is always True.
    return MockAgentProvider()
