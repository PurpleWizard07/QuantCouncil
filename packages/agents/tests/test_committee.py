"""Tests for pure committee orchestration and the deterministic veto step.

Uses ``MockAgentProvider`` throughout (offline, deterministic, keyless) --
these tests are the end-to-end proof that a rejected-but-profitable backtest
cannot reach PAPER_TRADE, no matter what the raw CIO output says.
"""

from __future__ import annotations

from pydantic import BaseModel

from agents.committee import OVERRIDE_WARNING, ROLE_ORDER, run_committee
from agents.providers.base import AgentProvider
from agents.providers.mock import MockAgentProvider
from agents.roles import AgentRole


def _context(total_return: float, approved: bool) -> dict:
    return {
        "strategy": {"name": "sma_cross", "rules_summary": "SMA20/50 crossover"},
        "metrics": {
            "total_return": total_return,
            "sharpe": 0.8,
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
            "warnings": [],
            "policy_version": "1.0.0",
        },
        "trades_summary": {"count": 40, "sample": []},
        "symbol": "RELIANCE",
        "dates": {"start": "2024-01-01", "end": "2024-06-01"},
        "backtest_id": "bt-001",
        "risk_evaluation_id": "re-001",
    }


class SpyProvider(AgentProvider):
    """Delegates to MockAgentProvider but records every (role, payload) call,
    so tests can inspect exactly what each role was given."""

    name = "spy"

    def __init__(self) -> None:
        self._inner = MockAgentProvider()
        self.calls: list[tuple[AgentRole, dict]] = []

    @classmethod
    def is_configured(cls) -> bool:
        return True

    def generate(
        self, role: AgentRole, system_prompt: str, payload: dict, schema: type[BaseModel]
    ) -> BaseModel:
        self.calls.append((role, payload))
        return self._inner.generate(role, system_prompt, payload, schema)


class TestApprovedRiskPositiveReturn:
    def test_final_paper_trade_no_override(self) -> None:
        result = run_committee(MockAgentProvider(), _context(total_return=0.15, approved=True))
        assert result.cio_raw.decision == "PAPER_TRADE"
        assert result.final_decision.decision == "PAPER_TRADE"
        assert result.final_decision.approved_by_risk is True
        assert result.override_warning is None
        assert result.provider_name == "mock"


class TestRejectedRiskPositiveReturn:
    def test_raw_paper_trade_overridden_to_no_trade(self) -> None:
        result = run_committee(MockAgentProvider(), _context(total_return=0.15, approved=False))
        assert result.cio_raw.decision == "PAPER_TRADE"
        assert result.final_decision.decision == "NO_TRADE"
        assert result.final_decision.approved_by_risk is False
        assert result.override_warning == OVERRIDE_WARNING
        assert result.override_warning == (
            "CIO raw PAPER_TRADE overridden because risk engine rejected the backtest."
        )


class TestApprovedRiskNegativeReturn:
    def test_no_trade_without_override(self) -> None:
        result = run_committee(MockAgentProvider(), _context(total_return=-0.05, approved=True))
        assert result.cio_raw.decision == "NO_TRADE"
        assert result.final_decision.decision == "NO_TRADE"
        assert result.final_decision.approved_by_risk is True
        assert result.override_warning is None


class TestRejectedRiskZeroReturn:
    def test_watchlist_is_not_touched_by_veto(self) -> None:
        result = run_committee(MockAgentProvider(), _context(total_return=0.0, approved=False))
        assert result.cio_raw.decision == "WATCHLIST"
        assert result.final_decision.decision == "WATCHLIST"
        assert result.override_warning is None


class TestAuditRefs:
    def test_audit_refs_come_from_context(self) -> None:
        result = run_committee(MockAgentProvider(), _context(total_return=0.15, approved=True))
        refs = result.final_decision.audit_refs
        assert refs.backtest_id == "bt-001"
        assert refs.risk_evaluation_id == "re-001"
        assert refs.agent_decision_ids == []


class TestRoleOrdering:
    def test_ordered_outputs_matches_role_order(self) -> None:
        result = run_committee(MockAgentProvider(), _context(total_return=0.1, approved=True))
        roles_in_result = [role for role, _ in result.ordered_outputs()]
        assert roles_in_result == list(ROLE_ORDER)
        assert roles_in_result == [
            AgentRole.TECHNICAL_ANALYST,
            AgentRole.QUANT_RESEARCHER,
            AgentRole.BULL,
            AgentRole.BEAR,
            AgentRole.RISK_NARRATOR,
            AgentRole.CIO,
        ]

    def test_provider_called_in_role_order(self) -> None:
        spy = SpyProvider()
        run_committee(spy, _context(total_return=0.1, approved=True))
        called_roles = [role for role, _ in spy.calls]
        assert called_roles == list(ROLE_ORDER)


class TestPriorSummariesFlowForward:
    def test_first_role_gets_no_committee_so_far(self) -> None:
        spy = SpyProvider()
        run_committee(spy, _context(total_return=0.1, approved=True))
        first_role, first_payload = spy.calls[0]
        assert first_role == AgentRole.TECHNICAL_ANALYST
        assert "committee_so_far" not in first_payload

    def test_later_roles_see_prior_summaries(self) -> None:
        spy = SpyProvider()
        run_committee(spy, _context(total_return=0.1, approved=True))
        calls_by_role = dict(spy.calls)

        bull_payload = calls_by_role[AgentRole.BULL]
        assert "committee_so_far" in bull_payload
        assert AgentRole.TECHNICAL_ANALYST.value in bull_payload["committee_so_far"]
        assert AgentRole.QUANT_RESEARCHER.value in bull_payload["committee_so_far"]
        # Bull/Bear haven't run yet relative to themselves.
        assert AgentRole.BULL.value not in bull_payload["committee_so_far"]

    def test_cio_sees_risk_narrators_plain_english_verdict(self) -> None:
        spy = SpyProvider()
        result = run_committee(spy, _context(total_return=0.1, approved=True))
        calls_by_role = dict(spy.calls)
        cio_payload = calls_by_role[AgentRole.CIO]
        narrator_entry = cio_payload["committee_so_far"][AgentRole.RISK_NARRATOR.value]
        assert narrator_entry == result.risk_narrator.plain_english_verdict

    def test_context_fields_present_in_every_payload(self) -> None:
        spy = SpyProvider()
        run_committee(spy, _context(total_return=0.1, approved=True))
        for _role, payload in spy.calls:
            assert payload["symbol"] == "RELIANCE"
            assert payload["metrics"]["total_return"] == 0.1
            assert payload["risk_evaluation"]["approved"] is True
            # Internal audit ids must not leak into agent payloads.
            assert "backtest_id" not in payload
            assert "risk_evaluation_id" not in payload
