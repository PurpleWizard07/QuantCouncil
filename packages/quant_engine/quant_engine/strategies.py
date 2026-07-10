"""Built-in strategy definitions.

The three initial strategies from docs/strategy-format.md, defined verbatim
as plain-dict module constants so the rest of the codebase can load,
validate, and backtest them without any JSON file I/O. Universe lists are
the five-symbol samples used in the doc; production definitions loading the
full NIFTY 50 constituent list are the API layer's responsibility, not this
package's.

Callers must not mutate the module constants (``SMA_CROSSOVER``,
``RSI_MEAN_REVERSION``, ``VOLUME_BREAKOUT``, ``BUILTIN_STRATEGIES``)
directly -- call :func:`get_builtin_strategies` instead, which returns deep
copies.
"""

from __future__ import annotations

import copy

_SAMPLE_UNIVERSE = ["RELIANCE", "TCS", "HDFCBANK", "INFY", "ICICIBANK"]

SMA_CROSSOVER: dict = {
    "name": "sma_crossover_20_50",
    "description": (
        "Enter long when SMA(20) crosses above SMA(50); exit when SMA(20) "
        "crosses below SMA(50). 5% stop-loss."
    ),
    "universe": list(_SAMPLE_UNIVERSE),
    "timeframe": "1d",
    "direction": "long_only",
    "entry": {
        "all": [
            {
                "indicator": "sma",
                "params": {"window": 20},
                "op": "crosses_above",
                "target": {"indicator": "sma", "params": {"window": 50}},
            }
        ]
    },
    "exit": {
        "all": [
            {
                "indicator": "sma",
                "params": {"window": 20},
                "op": "crosses_below",
                "target": {"indicator": "sma", "params": {"window": 50}},
            }
        ]
    },
    "stop_loss": {"type": "percent", "value": 0.05},
    "position_sizing": {"type": "risk_percent", "value": 0.01},
}

RSI_MEAN_REVERSION: dict = {
    "name": "rsi_mean_reversion_14",
    "description": (
        "Enter long when RSI(14) drops below 30 (oversold); exit when "
        "RSI(14) rises above 55. 5% stop-loss."
    ),
    "universe": list(_SAMPLE_UNIVERSE),
    "timeframe": "1d",
    "direction": "long_only",
    "entry": {
        "all": [
            {
                "indicator": "rsi",
                "params": {"window": 14},
                "op": "less_than",
                "value": 30,
            }
        ]
    },
    "exit": {
        "all": [
            {
                "indicator": "rsi",
                "params": {"window": 14},
                "op": "greater_than",
                "value": 55,
            }
        ]
    },
    "stop_loss": {"type": "percent", "value": 0.05},
    "position_sizing": {"type": "risk_percent", "value": 0.01},
}

VOLUME_BREAKOUT: dict = {
    "name": "volume_breakout_swing_20",
    "description": (
        "Enter long on a 20-day closing-high breakout confirmed by volume "
        "above 1.5x its 20-day average; exit when close falls below "
        "SMA(20). 7% stop-loss."
    ),
    "universe": list(_SAMPLE_UNIVERSE),
    "timeframe": "1d",
    "direction": "long_only",
    "entry": {
        "all": [
            {
                "indicator": "close",
                "params": {},
                "op": "greater_than",
                "target": {"indicator": "highest_close", "params": {"window": 20}},
            },
            {
                "indicator": "volume",
                "params": {},
                "op": "greater_than",
                "target": {
                    "indicator": "volume_sma",
                    "params": {"window": 20},
                    "multiplier": 1.5,
                },
            },
        ]
    },
    "exit": {
        "all": [
            {
                "indicator": "close",
                "params": {},
                "op": "less_than",
                "target": {"indicator": "sma", "params": {"window": 20}},
            }
        ]
    },
    "stop_loss": {"type": "percent", "value": 0.07},
    "position_sizing": {"type": "risk_percent", "value": 0.01},
}

BUILTIN_STRATEGIES: list[dict] = [SMA_CROSSOVER, RSI_MEAN_REVERSION, VOLUME_BREAKOUT]


def get_builtin_strategies() -> list[dict]:
    """Return deep copies of the built-in strategy definitions.

    Callers are free to mutate the returned list and its dict elements; the
    module constants above (and ``BUILTIN_STRATEGIES``) are never affected.

    Returns:
        A new list of deep copies, in the order
        ``[SMA_CROSSOVER, RSI_MEAN_REVERSION, VOLUME_BREAKOUT]``.
    """
    return [copy.deepcopy(strategy) for strategy in BUILTIN_STRATEGIES]
