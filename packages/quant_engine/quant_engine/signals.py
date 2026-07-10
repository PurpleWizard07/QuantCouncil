"""Signal generation from declarative strategy rules.

Turns a strategy definition (a rules dict, see docs/strategy-format.md) plus
OHLCV data into deterministic entry/exit signals. Long-only in v1. All
indicator math is delegated to ``quant_engine.indicators`` -- this module
only interprets the condition tree and never reimplements indicator formulas.

Column naming scheme (intermediate/audit columns added to the returned
frame, in addition to ``entry_signal`` / ``exit_signal`` / ``stop_loss_price``):
    - ``close`` / ``volume``: the raw input columns are reused as-is; no
      duplicate column is added.
    - ``sma`` / ``ema`` / ``rsi`` / ``volume_sma`` / ``highest_close``:
      ``f"{indicator}_{window}"``, e.g. ``sma_20``, ``rsi_14``,
      ``volume_sma_20``, ``highest_close_20``.
    - Every occurrence of the same ``(indicator, params)`` pair anywhere in
      the entry/exit trees resolves to the *same* column (computed once; a
      later reference reuses it by name).
    - A comparison ``target`` whose ``multiplier`` is not ``1.0`` gets an
      additional column ``f"{base_column}_x{multiplier:g}"`` (e.g.
      ``volume_sma_20_x1.5``) holding the already-multiplied series that was
      actually compared against; the un-multiplied base column is still
      present separately. ``multiplier == 1.0`` reuses the base column and
      adds nothing extra.

``highest_close`` semantics (interpreter-level fix, see
docs/strategy-format.md): the doc defines ``highest_close(window)`` as the
highest close of the ``window`` bars *prior to* the current bar, excluding
it. ``quant_engine.indicators.highest_close`` is inclusive of the current
bar (a thin wrapper over ``rolling_high``). This module bridges that gap by
computing ``indicators.highest_close(close, window).shift(1)`` -- the shift
happens HERE, not in ``indicators.py``, which stays a general-purpose
(inclusive) rolling-max primitive. As a result the ``highest_close_<window>``
column stores the *shifted* (exclusive) series, so a volume-breakout entry
``close greater_than highest_close(20)`` can actually fire on a new 20-day
closing high -- with the inclusive indicator the current bar would always be
part of its own rolling max, so ``close > max(close)`` (including itself)
could never be true.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from quant_engine import indicators
from quant_engine.strategy import validate_strategy

_REQUIRED_COLUMNS = ("date", "open", "high", "low", "close", "volume")


def generate_signals(df: pd.DataFrame, rules: dict) -> pd.DataFrame:
    """Generate long-only entry/exit signals from a declarative rules dict.

    The ``rules`` dict follows the strategy definition format documented in
    docs/strategy-format.md (entry/exit condition trees, stop-loss
    specification, indicator parameters); it is validated via
    ``quant_engine.strategy.validate_strategy`` before use. Signals on bar
    ``t`` are computed only from data available through bar ``t`` (no
    lookahead -- crosses compare against ``shift(1)``, never a negative
    shift).

    Args:
        df: OHLCV DataFrame with columns
            ``[date, open, high, low, close, volume]``, ascending date,
            tz-naive, no duplicate dates, no NaN rows (the data-connector
            contract). Never mutated.
        rules: Strategy rules dict per docs/strategy-format.md.

    Returns:
        A copy of ``df`` with added columns:
            - ``entry_signal`` (bool): True on bars where the entry
              condition tree evaluates true.
            - ``exit_signal`` (bool): True on bars where the exit condition
              tree evaluates true.
            - ``stop_loss_price`` (float64): on entry bars,
              ``close * (1 - stop_loss.value)``; NaN elsewhere. This is
              INDICATIVE only -- it is derived from the signal bar's close,
              not the actual fill price. Per the fill model, entries fill at
              the *next* bar's open, so the backtester must recompute the
              real stop from the actual fill price; this column exists for
              auditability of the signal, not as the authoritative stop.
            - Intermediate indicator columns per the naming scheme documented
              in this module's docstring, for auditability.
        ``entry_signal`` / ``exit_signal`` are always bool dtype with no NaN:
        comparisons against NaN (e.g. in the indicator warm-up region)
        evaluate to False, not NaN.

    Raises:
        ValueError: If ``df`` is missing a required column or is empty.
        StrategyValidationError: If ``rules`` fails schema validation.
    """
    normalized = validate_strategy(rules)

    missing_columns = [col for col in _REQUIRED_COLUMNS if col not in df.columns]
    if missing_columns:
        raise ValueError(
            f"df is missing required column(s) {missing_columns}; "
            f"expected columns {list(_REQUIRED_COLUMNS)}"
        )
    if df.empty:
        raise ValueError("df must not be empty")

    work = df.copy()

    entry_signal = _evaluate_tree(work, normalized["entry"]).fillna(False).astype(bool)
    exit_signal = _evaluate_tree(work, normalized["exit"]).fillna(False).astype(bool)

    work["entry_signal"] = entry_signal
    work["exit_signal"] = exit_signal

    stop_loss_value = normalized["stop_loss"]["value"]
    stop_loss_price = pd.Series(np.nan, index=work.index, dtype="float64")
    stop_loss_price.loc[entry_signal] = work.loc[entry_signal, "close"] * (1.0 - stop_loss_value)
    work["stop_loss_price"] = stop_loss_price

    return work


def _indicator_column_name(indicator: str, params: dict) -> str:
    """Deterministic output column name for an ``(indicator, params)`` pair."""
    if indicator in ("close", "volume"):
        return indicator
    return f"{indicator}_{params['window']}"


def _ensure_indicator_column(work: pd.DataFrame, indicator: str, params: dict) -> pd.Series:
    """Compute (if not already present) and return the column for ``indicator``.

    Mutates ``work`` in place by adding the computed column when it is not
    already present, so repeated references to the same ``(indicator,
    params)`` pair reuse the same column instead of recomputing it. ``work``
    is always the interpreter's own copy of the input frame, never the
    caller's original ``df``.
    """
    col_name = _indicator_column_name(indicator, params)
    if indicator in ("close", "volume"):
        return work[col_name]

    if col_name not in work.columns:
        window = params["window"]
        if indicator == "sma":
            work[col_name] = indicators.sma(work["close"], window)
        elif indicator == "ema":
            work[col_name] = indicators.ema(work["close"], window)
        elif indicator == "rsi":
            work[col_name] = indicators.rsi(work["close"], window)
        elif indicator == "volume_sma":
            work[col_name] = indicators.volume_sma(work["volume"], window)
        elif indicator == "highest_close":
            # Interpreter-level fix: prior-N-bars high EXCLUDING the current
            # bar. See module docstring.
            work[col_name] = indicators.highest_close(work["close"], window).shift(1)
        else:  # pragma: no cover - validate_strategy rejects unknown indicators upstream.
            raise AssertionError(f"unreachable: unknown indicator {indicator!r}")

    return work[col_name]


def _resolve_target_series(work: pd.DataFrame, target: dict) -> pd.Series:
    """Resolve a condition's ``target`` to the (possibly multiplier-scaled) series."""
    base = _ensure_indicator_column(work, target["indicator"], target["params"])
    multiplier = target["multiplier"]
    if multiplier == 1.0:
        return base

    base_col_name = _indicator_column_name(target["indicator"], target["params"])
    mult_col_name = f"{base_col_name}_x{multiplier:g}"
    if mult_col_name not in work.columns:
        work[mult_col_name] = base * multiplier
    return work[mult_col_name]


def _apply_op(op: str, left: pd.Series, right: pd.Series | float) -> pd.Series:
    """Elementwise/cross comparison. ``right`` may be a scalar (value case)."""
    if op == "greater_than":
        return left > right
    if op == "less_than":
        return left < right

    left_prev = left.shift(1)
    right_prev = right.shift(1) if isinstance(right, pd.Series) else right
    if op == "crosses_above":
        return (left_prev <= right_prev) & (left > right)
    if op == "crosses_below":
        return (left_prev >= right_prev) & (left < right)
    raise AssertionError(f"unreachable: unknown op {op!r}")  # validate_strategy rejects this upstream.


def _evaluate_condition(work: pd.DataFrame, condition: dict) -> pd.Series:
    left = _ensure_indicator_column(work, condition["indicator"], condition["params"])

    if "value" in condition:
        right: pd.Series | float = condition["value"]
    else:
        right = _resolve_target_series(work, condition["target"])

    result = _apply_op(condition["op"], left, right)
    # NaN operands already compare False under numpy/pandas semantics; fillna
    # is a defensive no-op that also normalizes dtype to plain bool.
    return result.fillna(False).astype(bool)


def _evaluate_tree(work: pd.DataFrame, tree: dict) -> pd.Series:
    if "all" in tree:
        children = [_evaluate_tree(work, child) for child in tree["all"]]
        result = children[0]
        for child in children[1:]:
            result = result & child
        return result

    if "any" in tree:
        children = [_evaluate_tree(work, child) for child in tree["any"]]
        result = children[0]
        for child in children[1:]:
            result = result | child
        return result

    return _evaluate_condition(work, tree)
