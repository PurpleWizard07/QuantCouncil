"""Tests for provider selection: manual by name, and automatic priority.

No network is exercised: Ollama's reachability probe is monkeypatched in
every test that touches it (including indirectly via ``resolve_auto``), so
there is no dependency on whether a local Ollama server happens to be
running on the machine executing the tests.
"""

from __future__ import annotations

import pytest

from agents.providers.anthropic_provider import AnthropicAgentProvider
from agents.providers.base import ProviderNotConfiguredError
from agents.providers.gemini_provider import GeminiAgentProvider
from agents.providers.mock import MockAgentProvider
from agents.providers.ollama_provider import OllamaAgentProvider
from agents.providers.openrouter_provider import OpenRouterAgentProvider
from agents.providers.registry import AUTO_PRIORITY, PROVIDER_CLASSES, get_provider, resolve_auto

ALL_KEY_ENV_VARS = ["ANTHROPIC_API_KEY", "GEMINI_API_KEY", "OPENROUTER_API_KEY"]


def _clear_all_cloud_keys(monkeypatch: pytest.MonkeyPatch) -> None:
    for var in ALL_KEY_ENV_VARS:
        monkeypatch.delenv(var, raising=False)
    monkeypatch.delenv("OLLAMA_BASE_URL", raising=False)


def _force_ollama_unreachable(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(OllamaAgentProvider, "_probe", staticmethod(lambda base_url: False))


def _force_ollama_reachable(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(OllamaAgentProvider, "_probe", staticmethod(lambda base_url: True))


class TestProviderClassesAndPriority:
    def test_provider_classes_has_all_five(self) -> None:
        assert set(PROVIDER_CLASSES) == {"mock", "anthropic", "gemini", "openrouter", "ollama"}

    def test_auto_priority_order(self) -> None:
        assert AUTO_PRIORITY == ["anthropic", "gemini", "openrouter", "ollama", "mock"]

    def test_mock_is_last_in_priority(self) -> None:
        assert AUTO_PRIORITY[-1] == "mock"


class TestGetProviderMock:
    def test_get_provider_mock_works(self) -> None:
        provider = get_provider("mock")
        assert isinstance(provider, MockAgentProvider)
        assert provider.name == "mock"

    def test_get_provider_auto_default_behavior_never_raises(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Regardless of local machine configuration, "auto" always resolves
        to *some* provider -- it never raises."""
        provider = get_provider("auto")
        assert provider.name in PROVIDER_CLASSES


class TestGetProviderUnknownName:
    def test_unknown_name_raises_value_error(self) -> None:
        with pytest.raises(ValueError) as exc_info:
            get_provider("chatgpt")
        message = str(exc_info.value)
        assert "chatgpt" in message
        for name in PROVIDER_CLASSES:
            assert name in message


class TestManualModeNotConfigured:
    def test_anthropic_manual_without_key_raises(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
        with pytest.raises(ProviderNotConfiguredError) as exc_info:
            get_provider("anthropic")
        assert "ANTHROPIC_API_KEY" in str(exc_info.value)

    def test_gemini_manual_without_key_raises(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv("GEMINI_API_KEY", raising=False)
        with pytest.raises(ProviderNotConfiguredError) as exc_info:
            get_provider("gemini")
        assert "GEMINI_API_KEY" in str(exc_info.value)

    def test_openrouter_manual_without_key_raises(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
        with pytest.raises(ProviderNotConfiguredError) as exc_info:
            get_provider("openrouter")
        assert "OPENROUTER_API_KEY" in str(exc_info.value)

    def test_manual_selection_never_falls_back_to_mock(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """An unconfigured manual selection must raise -- never silently
        return a MockAgentProvider instead."""
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
        with pytest.raises(ProviderNotConfiguredError):
            get_provider("anthropic")

    def test_ollama_manual_with_unreachable_base_raises(self, monkeypatch: pytest.MonkeyPatch) -> None:
        _force_ollama_unreachable(monkeypatch)
        with pytest.raises(ProviderNotConfiguredError) as exc_info:
            get_provider("ollama")
        assert "not reachable" in str(exc_info.value).lower()

    def test_ollama_manual_unroutable_port_raises(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Point at a real (but unroutable/closed) address instead of
        monkeypatching the probe -- the real probe's short timeout must
        still resolve this quickly and deterministically to 'not reachable'.
        """
        monkeypatch.setenv("OLLAMA_BASE_URL", "http://127.0.0.1:1")
        with pytest.raises(ProviderNotConfiguredError):
            get_provider("ollama")


class TestAutoResolution:
    def test_auto_with_nothing_configured_returns_mock(self, monkeypatch: pytest.MonkeyPatch) -> None:
        _clear_all_cloud_keys(monkeypatch)
        _force_ollama_unreachable(monkeypatch)
        provider = resolve_auto()
        assert isinstance(provider, MockAgentProvider)
        assert provider.name == "mock"

    def test_auto_with_anthropic_key_returns_anthropic_instance(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        _clear_all_cloud_keys(monkeypatch)
        _force_ollama_unreachable(monkeypatch)
        monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test-not-real")
        provider = resolve_auto()
        assert isinstance(provider, AnthropicAgentProvider)
        assert provider.name == "anthropic"

    def test_auto_priority_gemini_over_openrouter_and_ollama(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        _clear_all_cloud_keys(monkeypatch)
        _force_ollama_reachable(monkeypatch)  # ollama reachable but lower priority
        monkeypatch.setenv("GEMINI_API_KEY", "test-not-real")
        monkeypatch.setenv("OPENROUTER_API_KEY", "test-not-real")
        provider = resolve_auto()
        assert isinstance(provider, GeminiAgentProvider)
        assert provider.name == "gemini"

    def test_auto_falls_through_to_ollama_when_only_ollama_reachable(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        _clear_all_cloud_keys(monkeypatch)
        _force_ollama_reachable(monkeypatch)
        provider = resolve_auto()
        assert isinstance(provider, OllamaAgentProvider)
        assert provider.name == "ollama"

    def test_anthropic_takes_priority_over_everything(self, monkeypatch: pytest.MonkeyPatch) -> None:
        _clear_all_cloud_keys(monkeypatch)
        _force_ollama_reachable(monkeypatch)
        monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test-not-real")
        monkeypatch.setenv("GEMINI_API_KEY", "test-not-real")
        monkeypatch.setenv("OPENROUTER_API_KEY", "test-not-real")
        provider = resolve_auto()
        assert provider.name == "anthropic"
