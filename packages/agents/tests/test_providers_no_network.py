"""Transport-level tests for the four real providers -- zero real network.

Every HTTP/SDK call is monkeypatched to a canned in-memory response. This
covers: valid responses validate into the requested schema; malformed
responses raise ``ProviderResponseError``; and, as a hard guard rail, that no
cloud provider's transport is ever actually invoked when the app runs on the
mock provider or on "auto" with no credentials configured (the state every
test in this repo, and the app with zero LLM credentials, runs in).
"""

from __future__ import annotations

import json

import httpx
import pytest

from agents.committee import run_committee
from agents.providers.anthropic_provider import AnthropicAgentProvider
from agents.providers.base import ProviderError, ProviderResponseError
from agents.providers.gemini_provider import GeminiAgentProvider
from agents.providers.ollama_provider import OllamaAgentProvider
from agents.providers.openrouter_provider import OpenRouterAgentProvider
from agents.providers.registry import get_provider, resolve_auto
from agents.roles import AgentRole
from agents.schemas import TechnicalAnalystOutput

VALID_TECHNICAL_JSON = {
    "view": "BULLISH",
    "confidence": 0.5,
    "signals": ["total_return=0.10"],
    "warnings": [],
    "summary": "ok",
}
INVALID_TECHNICAL_JSON = {
    # "SIDEWAYS" is not a valid Literal member -> schema validation must fail.
    "view": "SIDEWAYS",
    "confidence": 0.5,
    "signals": [],
    "warnings": [],
    "summary": "ok",
}


class _FakeHTTPResponse:
    """Minimal stand-in for an ``httpx.Response`` used by the real providers."""

    def __init__(self, json_data: dict, status_code: int = 200) -> None:
        self._json_data = json_data
        self.status_code = status_code

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            request = httpx.Request("POST", "https://example.invalid")
            response = httpx.Response(self.status_code, request=request)
            raise httpx.HTTPStatusError("error", request=request, response=response)

    def json(self) -> dict:
        return self._json_data


# ---------------------------------------------------------------------------
# Anthropic
# ---------------------------------------------------------------------------


class _FakeParsedMessage:
    def __init__(self, stop_reason: str, parsed_output) -> None:
        self.stop_reason = stop_reason
        self.parsed_output = parsed_output


class _FakeAnthropicMessages:
    def __init__(self, response: _FakeParsedMessage) -> None:
        self._response = response

    def parse(self, **kwargs):
        return self._response


class _FakeAnthropicClient:
    def __init__(self, response: _FakeParsedMessage) -> None:
        self.messages = _FakeAnthropicMessages(response)


class TestAnthropicProviderNoNetwork:
    def test_valid_response_validates(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test-not-real")
        import anthropic

        valid_output = TechnicalAnalystOutput(**VALID_TECHNICAL_JSON)
        fake_response = _FakeParsedMessage(stop_reason="end_turn", parsed_output=valid_output)
        monkeypatch.setattr(anthropic, "Anthropic", lambda *a, **kw: _FakeAnthropicClient(fake_response))

        provider = AnthropicAgentProvider()
        result = provider.generate(
            AgentRole.TECHNICAL_ANALYST, "sys", {"x": 1}, TechnicalAnalystOutput
        )
        assert result == valid_output

    def test_malformed_response_raises_provider_response_error(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test-not-real")
        import anthropic

        # The SDK sets parsed_output to None when it could not parse the
        # model's output into the requested schema.
        fake_response = _FakeParsedMessage(stop_reason="end_turn", parsed_output=None)
        monkeypatch.setattr(anthropic, "Anthropic", lambda *a, **kw: _FakeAnthropicClient(fake_response))

        provider = AnthropicAgentProvider()
        with pytest.raises(ProviderResponseError):
            provider.generate(AgentRole.TECHNICAL_ANALYST, "sys", {"x": 1}, TechnicalAnalystOutput)

    def test_refusal_stop_reason_raises_provider_error(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test-not-real")
        import anthropic

        fake_response = _FakeParsedMessage(stop_reason="refusal", parsed_output=None)
        monkeypatch.setattr(anthropic, "Anthropic", lambda *a, **kw: _FakeAnthropicClient(fake_response))

        provider = AnthropicAgentProvider()
        with pytest.raises(ProviderError):
            provider.generate(AgentRole.TECHNICAL_ANALYST, "sys", {"x": 1}, TechnicalAnalystOutput)


# ---------------------------------------------------------------------------
# Gemini
# ---------------------------------------------------------------------------


def _gemini_body(text: str) -> dict:
    return {"candidates": [{"content": {"parts": [{"text": text}]}}]}


class TestGeminiProviderNoNetwork:
    def test_valid_response_validates(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("GEMINI_API_KEY", "test-not-real")
        fake_response = _FakeHTTPResponse(_gemini_body(json.dumps(VALID_TECHNICAL_JSON)))
        monkeypatch.setattr(httpx, "post", lambda *a, **kw: fake_response)

        provider = GeminiAgentProvider()
        result = provider.generate(
            AgentRole.TECHNICAL_ANALYST, "sys", {"x": 1}, TechnicalAnalystOutput
        )
        assert isinstance(result, TechnicalAnalystOutput)
        assert result.view == "BULLISH"

    def test_schema_invalid_response_raises(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("GEMINI_API_KEY", "test-not-real")
        fake_response = _FakeHTTPResponse(_gemini_body(json.dumps(INVALID_TECHNICAL_JSON)))
        monkeypatch.setattr(httpx, "post", lambda *a, **kw: fake_response)

        provider = GeminiAgentProvider()
        with pytest.raises(ProviderResponseError):
            provider.generate(AgentRole.TECHNICAL_ANALYST, "sys", {"x": 1}, TechnicalAnalystOutput)

    def test_non_json_text_raises(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("GEMINI_API_KEY", "test-not-real")
        fake_response = _FakeHTTPResponse(_gemini_body("not json at all"))
        monkeypatch.setattr(httpx, "post", lambda *a, **kw: fake_response)

        provider = GeminiAgentProvider()
        with pytest.raises(ProviderResponseError):
            provider.generate(AgentRole.TECHNICAL_ANALYST, "sys", {"x": 1}, TechnicalAnalystOutput)


# ---------------------------------------------------------------------------
# OpenRouter
# ---------------------------------------------------------------------------


def _openrouter_body(content: str) -> dict:
    return {"choices": [{"message": {"content": content}}]}


class TestOpenRouterProviderNoNetwork:
    def test_valid_response_validates(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("OPENROUTER_API_KEY", "test-not-real")
        fake_response = _FakeHTTPResponse(_openrouter_body(json.dumps(VALID_TECHNICAL_JSON)))
        monkeypatch.setattr(httpx, "post", lambda *a, **kw: fake_response)

        provider = OpenRouterAgentProvider()
        result = provider.generate(
            AgentRole.TECHNICAL_ANALYST, "sys", {"x": 1}, TechnicalAnalystOutput
        )
        assert isinstance(result, TechnicalAnalystOutput)

    def test_schema_invalid_response_raises(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("OPENROUTER_API_KEY", "test-not-real")
        fake_response = _FakeHTTPResponse(_openrouter_body(json.dumps(INVALID_TECHNICAL_JSON)))
        monkeypatch.setattr(httpx, "post", lambda *a, **kw: fake_response)

        provider = OpenRouterAgentProvider()
        with pytest.raises(ProviderResponseError):
            provider.generate(AgentRole.TECHNICAL_ANALYST, "sys", {"x": 1}, TechnicalAnalystOutput)


# ---------------------------------------------------------------------------
# Ollama
# ---------------------------------------------------------------------------


def _ollama_body(content: str) -> dict:
    return {"message": {"content": content}}


class TestOllamaProviderNoNetwork:
    def test_valid_response_validates(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(OllamaAgentProvider, "_probe", staticmethod(lambda base_url: True))
        fake_response = _FakeHTTPResponse(_ollama_body(json.dumps(VALID_TECHNICAL_JSON)))
        monkeypatch.setattr(httpx, "post", lambda *a, **kw: fake_response)

        provider = OllamaAgentProvider()
        result = provider.generate(
            AgentRole.TECHNICAL_ANALYST, "sys", {"x": 1}, TechnicalAnalystOutput
        )
        assert isinstance(result, TechnicalAnalystOutput)

    def test_schema_invalid_response_raises(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(OllamaAgentProvider, "_probe", staticmethod(lambda base_url: True))
        fake_response = _FakeHTTPResponse(_ollama_body(json.dumps(INVALID_TECHNICAL_JSON)))
        monkeypatch.setattr(httpx, "post", lambda *a, **kw: fake_response)

        provider = OllamaAgentProvider()
        with pytest.raises(ProviderResponseError):
            provider.generate(AgentRole.TECHNICAL_ANALYST, "sys", {"x": 1}, TechnicalAnalystOutput)


# ---------------------------------------------------------------------------
# Guard rail: mock / auto-without-keys never touches a cloud transport.
# ---------------------------------------------------------------------------


class TestNoCloudCallsWithoutCredentials:
    def test_mock_and_auto_never_invoke_httpx_or_anthropic_sdk(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        def _fail_post(*args, **kwargs):
            raise AssertionError("httpx.post must not be called when using mock/auto-without-keys")

        monkeypatch.setattr(httpx, "post", _fail_post)

        import anthropic

        def _fail_anthropic(*args, **kwargs):
            raise AssertionError("anthropic.Anthropic must not be constructed without a key")

        monkeypatch.setattr(anthropic, "Anthropic", _fail_anthropic)

        for var in ("ANTHROPIC_API_KEY", "GEMINI_API_KEY", "OPENROUTER_API_KEY"):
            monkeypatch.delenv(var, raising=False)
        monkeypatch.setattr(OllamaAgentProvider, "_probe", staticmethod(lambda base_url: False))

        mock_provider = get_provider("mock")
        assert mock_provider.name == "mock"

        auto_provider = resolve_auto()
        assert auto_provider.name == "mock"

        context = {
            "strategy": {"name": "sma_cross", "rules_summary": "SMA20/50"},
            "metrics": {
                "total_return": 0.1,
                "sharpe": 0.5,
                "profit_factor": 1.3,
                "num_trades": 35,
                "win_rate": 0.5,
                "max_drawdown": 0.1,
            },
            "risk_evaluation": {
                "decision": "APPROVED",
                "approved": True,
                "risk_score": 90,
                "failed_rules": [],
                "warnings": [],
                "policy_version": "1.0.0",
            },
            "trades_summary": {"count": 35, "sample": []},
            "symbol": "TCS",
            "dates": {"start": "2024-01-01", "end": "2024-06-01"},
            "backtest_id": "bt-1",
            "risk_evaluation_id": "re-1",
        }
        result = run_committee(auto_provider, context)
        assert result.provider_name == "mock"
