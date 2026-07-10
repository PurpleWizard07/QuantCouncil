"""QuantCouncil quantitative engine.

Deterministic calculations only -- this package is the source of truth for all
numbers in QuantCouncil. Indicators, signal generation, backtests, and
performance metrics are computed here with plain pandas/numpy code that is
reproducible and testable.

LLM agents may reason about, summarize, or debate the outputs of this package,
but they must NEVER invent calculations or fake backtest results. If a number
did not come from this package (or another deterministic engine), it does not
exist.

Status: indicators are implemented (Phase 2). Signals, backtesting, and
metrics remain typed stubs raising NotImplementedError until Phase 3.
"""

__version__ = "0.1.0"
