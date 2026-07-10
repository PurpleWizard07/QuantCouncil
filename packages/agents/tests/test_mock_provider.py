"""Tests for the offline, deterministic MockAgentProvider.

Covers: every role produces a validated schema instance; identical payloads
produce byte-identical output (determinism); and THE CIO RAW RULE, which is
the mechanism that exercises the deterministic veto override in
``agents.committee.run_committee`` -- the mock CIO ignores risk approval
entirely and keys off ``metrics.total_return`` alone.
"""

from __future__ import annotations

from agents.providers.mock import MockAgentProvider
from agents.roles import AgentRole
from agents.schemas import (
    BearCaseOutput,
    BullCaseOutput,
    CIORawOutput,
    QuantResearcherOutput,
    RiskNarratorOutput,
    ROLE_OUTPUT_SCHEMAS,
    TechnicalAnalystOutput,
)


def _payload(total_return: float = 0.1, approved: bool = True) -> dict:
    return {
        "strategy": {"name": "sma_cross", "rules_summary": "SMA20/50 crossover"},
        "metrics": {
            "total_return": total_return,
            "sharpe": 0.9,
            "profit_factor": 1.6,
            "num_trades": 40,
            "win_rate": 0.55,
            "max_drawdown": 0.12,
        },
        "risk_evaluation": {
            "decision": "APPROVED" if approved else "REJECTED",
            "approved": approved,
            "risk_score": 80 if approved else 30,
            "failed_rules": [] if approved else ["max_drawdown_exceeded"],
            "warnings": ["low sample size"],
            "policy_version": "1.0.0",
        },
        "trades_summary": {"count": 40, "sample": []},
        "symbol": "RELIANCE",
        "dates": {"start": "2024-01-01", "end": "2024-06-01"},
    }


class TestAllRolesProduceValidOutput:
    def test_technical_analyst(self) -> None:
        provider = MockAgentProvider()
        out = provider.generate(
            AgentRole.TECHNICAL_ANALYST, "sys", _payload(), TechnicalAnalystOutput
        )
        assert isinstance(out, TechnicalAnalystOutput)

    def test_quant_researcher(self) -> None:
        provider = MockAgentProvider()
        out = provider.generate(
            AgentRole.QUANT_RESEARCHER, "sys", _payload(), QuantResearcherOutput
        )
        assert isinstance(out, QuantResearcherOutput)

    def test_bull(self) -> None:
        provider = MockAgentProvider()
        out = provider.generate(AgentRole.BULL, "sys", _payload(), BullCaseOutput)
        assert isinstance(out, BullCaseOutput)

    def test_bear(self) -> None:
        provider = MockAgentProvider()
        out = provider.generate(AgentRole.BEAR, "sys", _payload(), BearCaseOutput)
        assert isinstance(out, BearCaseOutput)

    def test_risk_narrator(self) -> None:
        provider = MockAgentProvider()
        out = provider.generate(
            AgentRole.RISK_NARRATOR, "sys", _payload(approved=False), RiskNarratorOutput
        )
        assert isinstance(out, RiskNarratorOutput)
        assert "max_drawdown_exceeded" in out.failed_rules_explained[0]

    def test_cio(self) -> None:
        provider = MockAgentProvider()
        out = provider.generate(AgentRole.CIO, "sys", _payload(), CIORawOutput)
        assert isinstance(out, CIORawOutput)

    def test_every_role_via_role_output_schemas(self) -> None:
        provider = MockAgentProvider()
        for role, schema in ROLE_OUTPUT_SCHEMAS.items():
            out = provider.generate(role, "sys", _payload(), schema)
            assert isinstance(out, schema)


class TestDeterminism:
    def test_same_payload_twice_is_identical(self) -> None:
        provider = MockAgentProvider()
        payload = _payload()
        for role, schema in ROLE_OUTPUT_SCHEMAS.items():
            first = provider.generate(role, "sys", payload, schema)
            second = provider.generate(role, "sys", payload, schema)
            assert first == second
            assert first.model_dump() == second.model_dump()

    def test_two_separate_instances_agree(self) -> None:
        payload = _payload()
        first = MockAgentProvider().generate(AgentRole.CIO, "sys", payload, CIORawOutput)
        second = MockAgentProvider().generate(AgentRole.CIO, "sys", payload, CIORawOutput)
        assert first == second


class TestCIORawRule:
    """The mock CIO deliberately ignores risk approval; see mock.py docstring."""

    def test_positive_return_is_paper_trade_even_if_risk_rejected(self) -> None:
        provider = MockAgentProvider()
        payload = _payload(total_return=0.2, approved=False)
        out = provider.generate(AgentRole.CIO, "sys", payload, CIORawOutput)
        assert out.decision == "PAPER_TRADE"

    def test_positive_return_is_paper_trade_when_risk_approved(self) -> None:
        provider = MockAgentProvider()
        payload = _payload(total_return=0.2, approved=True)
        out = provider.generate(AgentRole.CIO, "sys", payload, CIORawOutput)
        assert out.decision == "PAPER_TRADE"

    def test_negative_return_is_no_trade(self) -> None:
        provider = MockAgentProvider()
        payload = _payload(total_return=-0.05, approved=True)
        out = provider.generate(AgentRole.CIO, "sys", payload, CIORawOutput)
        assert out.decision == "NO_TRADE"

    def test_zero_return_is_watchlist(self) -> None:
        provider = MockAgentProvider()
        payload = _payload(total_return=0.0, approved=True)
        out = provider.generate(AgentRole.CIO, "sys", payload, CIORawOutput)
        assert out.decision == "WATCHLIST"


class TestMockProviderConfiguration:
    def test_is_configured_is_always_true(self) -> None:
        assert MockAgentProvider.is_configured() is True

    def test_name_is_mock(self) -> None:
        assert MockAgentProvider.name == "mock"
