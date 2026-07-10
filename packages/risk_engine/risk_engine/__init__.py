"""QuantCouncil risk engine.

Deterministic, rule-based risk evaluation with veto power. The risk engine
takes backtest metrics (computed by quant_engine) and a RiskPolicy, and emits
a strict RiskEvaluationResult. No LLM is involved at any point.

Hard rule (codified in schemas across the project): if the risk engine does
not approve, the CIO agent decision MUST be NO_TRADE or WATCHLIST -- never
PAPER_TRADE.

Phase 4: ``evaluate()`` is fully implemented (see ``risk_engine.engine``), the
policy is YAML-backed (see ``risk_engine.policy`` and ``risk_policy.yaml``),
and ``RiskEvaluationResult`` (see ``risk_engine.schemas``) is the strict
output contract, including ``metrics_snapshot``/``policy_snapshot`` for audit.
"""

__version__ = "0.1.0"
