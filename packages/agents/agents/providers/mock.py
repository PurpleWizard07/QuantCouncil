"""Offline, deterministic, keyless provider used as the default fallback.

``MockAgentProvider`` never touches the network and requires no credentials,
so the whole app -- including every test in this repo -- works with zero LLM
access. It derives plausible-looking outputs purely from the payload it is
given (backtest metrics, the risk evaluation, prior-agent summaries): the
same payload always produces the same output.

THE CIO RAW RULE (read this before touching ``_cio``):
    decision = "PAPER_TRADE" if metrics.total_return > 0
             = "WATCHLIST"   if metrics.total_return == 0
             = "NO_TRADE"    otherwise

This rule DELIBERATELY ignores the risk evaluation's ``approved`` flag. That
is not a bug: it exists so that a rejected-but-profitable backtest drives the
raw CIO output to PAPER_TRADE, which forces ``agents.committee.run_committee``
to exercise its deterministic veto override end-to-end. The mock provider is
the thing that proves the veto works, not a well-behaved agent.
"""

from __future__ import annotations

from typing import Callable, ClassVar

from pydantic import BaseModel, ValidationError

from agents.providers.base import AgentProvider, ProviderResponseError
from agents.roles import AgentRole


def _clamp(value: float, low: float = 0.0, high: float = 1.0) -> float:
    return max(low, min(high, value))


class MockAgentProvider(AgentProvider):
    """Deterministic, offline stand-in for a real LLM backend."""

    name: ClassVar[str] = "mock"

    @classmethod
    def is_configured(cls) -> bool:
        """Always True: the mock needs no credentials and no network."""
        return True

    def generate(
        self,
        role: AgentRole,
        system_prompt: str,
        payload: dict,
        schema: type[BaseModel],
    ) -> BaseModel:
        """Build deterministic mock output for ``role`` and validate it.

        ``system_prompt`` is accepted for interface parity with real
        providers but is not used: the mock does not reason, it derives
        output mechanically from ``payload``.
        """
        builder: Callable[[dict], dict] | None = self._BUILDERS.get(role)
        if builder is None:
            raise ProviderResponseError(f"mock provider has no builder for role {role!r}")
        data = builder(self, payload)
        try:
            return schema.model_validate(data)
        except ValidationError as exc:
            raise ProviderResponseError(
                f"mock provider produced output that failed schema validation: {exc}"
            ) from exc

    # -- per-role builders -------------------------------------------------

    def _technical_analyst(self, payload: dict) -> dict:
        metrics = payload.get("metrics", {})
        total_return = float(metrics.get("total_return", 0.0))
        sharpe = float(metrics.get("sharpe", 0.0))
        symbol = payload.get("symbol", "the instrument")

        view = "BULLISH" if total_return > 0 else "BEARISH"
        confidence = _clamp(sharpe)
        signals = [
            f"total_return={total_return:.4f}",
            f"sharpe={sharpe:.4f}",
        ]
        warnings: list[str] = []
        if sharpe < 0:
            warnings.append("Sharpe ratio is negative.")
        return {
            "view": view,
            "confidence": confidence,
            "signals": signals,
            "warnings": warnings,
            "summary": (
                f"Technical read for {symbol}: {view.lower()} "
                f"(total_return={total_return:.4f}, sharpe={sharpe:.4f})."
            ),
        }

    def _quant_researcher(self, payload: dict) -> dict:
        metrics = payload.get("metrics", {})
        profit_factor = float(metrics.get("profit_factor", 0.0))
        num_trades = int(metrics.get("num_trades", 0))
        strategy = payload.get("strategy", {})
        strategy_name = strategy.get("name", "the strategy") if isinstance(strategy, dict) else "the strategy"

        if profit_factor >= 1.5 and num_trades >= 30:
            quality = "STRONG"
        elif profit_factor >= 1.2:
            quality = "ACCEPTABLE"
        else:
            quality = "WEAK"

        return {
            "strategy_quality": quality,
            "rule_interpretation": (
                f"{strategy_name} produced {num_trades} trades with a profit "
                f"factor of {profit_factor:.4f}."
            ),
            "strengths": [f"profit_factor={profit_factor:.4f}"] if profit_factor >= 1.2 else [],
            "weaknesses": [f"num_trades={num_trades}"] if num_trades < 30 else [],
            "improvement_ideas": (
                ["Collect more trades before drawing strong conclusions."] if num_trades < 30 else []
            ),
            "summary": (
                f"Backtest evidence for {strategy_name} is rated {quality} "
                f"(profit_factor={profit_factor:.4f}, num_trades={num_trades})."
            ),
        }

    def _bull(self, payload: dict) -> dict:
        metrics = payload.get("metrics", {})
        win_rate = _clamp(float(metrics.get("win_rate", 0.0)))
        total_return = float(metrics.get("total_return", 0.0))
        return {
            "case_strength": win_rate,
            "arguments": [f"win_rate={win_rate:.4f}", f"total_return={total_return:.4f}"],
            "best_case_scenario": (
                f"If the historical win rate of {win_rate:.4f} holds, the strategy "
                "continues to compound returns."
            ),
            "summary": f"Bull case strength {win_rate:.4f}, grounded in the backtest win rate.",
        }

    def _bear(self, payload: dict) -> dict:
        metrics = payload.get("metrics", {})
        win_rate = _clamp(float(metrics.get("win_rate", 0.0)))
        max_drawdown = float(metrics.get("max_drawdown", 0.0))
        case_strength = _clamp(1.0 - win_rate)
        return {
            "case_strength": case_strength,
            "risks": [f"win_rate={win_rate:.4f}", f"max_drawdown={max_drawdown:.4f}"],
            "failure_modes": [
                f"Only {win_rate:.4f} of historical trades were winners; a losing streak "
                "could erode capital quickly."
            ],
            "worst_case_scenario": (
                f"A drawdown near the historical max_drawdown of {max_drawdown:.4f} recurs."
            ),
            "summary": f"Bear case strength {case_strength:.4f}, grounded in the backtest loss profile.",
        }

    def _risk_narrator(self, payload: dict) -> dict:
        risk_eval = payload.get("risk_evaluation", {})
        decision = risk_eval.get("decision", "UNKNOWN")
        approved = bool(risk_eval.get("approved", False))
        risk_score = risk_eval.get("risk_score", "unknown")
        policy_version = risk_eval.get("policy_version", "unknown")
        failed_rules = risk_eval.get("failed_rules", []) or []
        warnings = risk_eval.get("warnings", []) or []

        return {
            "risk_summary": (
                f"Risk engine decision: {decision} (risk_score={risk_score}, "
                f"policy_version={policy_version})."
            ),
            "failed_rules_explained": [f"Failed rule: {rule}" for rule in failed_rules],
            "warnings_explained": [f"Warning: {warning}" for warning in warnings],
            "plain_english_verdict": (
                f"The risk engine {'approved' if approved else 'did not approve'} this "
                f"proposal under policy {policy_version}."
            ),
        }

    def _cio(self, payload: dict) -> dict:
        metrics = payload.get("metrics", {})
        total_return = float(metrics.get("total_return", 0.0))

        if total_return > 0:
            decision = "PAPER_TRADE"
        elif total_return == 0:
            decision = "WATCHLIST"
        else:
            decision = "NO_TRADE"

        return {
            "decision": decision,
            "summary": f"Committee view based on total_return={total_return:.4f}.",
            "reason": f"Raw CIO rule: total_return={total_return:.4f} maps to {decision}.",
            "conditions_to_reconsider": (
                ["Re-run once more trade history accumulates."] if decision != "PAPER_TRADE" else []
            ),
        }

    _BUILDERS: ClassVar[dict] = {
        AgentRole.TECHNICAL_ANALYST: _technical_analyst,
        AgentRole.QUANT_RESEARCHER: _quant_researcher,
        AgentRole.BULL: _bull,
        AgentRole.BEAR: _bear,
        AgentRole.RISK_NARRATOR: _risk_narrator,
        AgentRole.CIO: _cio,
    }
