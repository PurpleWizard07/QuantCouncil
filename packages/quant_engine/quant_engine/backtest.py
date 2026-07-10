"""Backtesting engine (deterministic, event-free daily simulation).

Simulates long-only strategies over daily bars for the NIFTY 50 universe.

Assumptions (v1, per project contract):
    - Fills are simulated at the NEXT day's open price
      (``next_day_open_fills=True``, the only supported mode -- setting it to
      False raises ``NotImplementedError``). A signal computed on day T's
      close can only be acted on at day T+1's open.
    - Slippage (``slippage_pct``) and transaction costs
      (``transaction_cost_pct``) are applied to every fill, always in the
      adverse direction for the account (higher price paid on buys, lower
      price received on sells).
    - Starting capital defaults to 1,000,000 INR (Rs 10,00,000), matching the
      paper portfolio rules.
    - Long-only; no shorting, no leverage; at most one open position at a
      time (no pyramiding); whole shares only.
    - Position sizing is constrained by three limits simultaneously: the
      strategy's risk-percent sizing rule, a max-allocation-per-trade cap
      (``max_allocation_pct``), and available cash.

Status: implemented (Phase 3). See ``Backtester.run_from_signals`` for the
full simulation semantics.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from datetime import date
from typing import Any

import pandas as pd

from quant_engine import metrics, signals

_BASE_OHLCV_COLUMNS = ["date", "open", "high", "low", "close", "volume"]
_SIGNAL_FRAME_COLUMNS = _BASE_OHLCV_COLUMNS + [
    "entry_signal",
    "exit_signal",
    "stop_loss_price",
]


@dataclass
class BacktestConfig:
    """Configuration for a single backtest run.

    Attributes:
        initial_capital: Starting capital in INR. Defaults to 1,000,000
            (Rs 10,00,000), matching the paper portfolio rules.
        start_date: First date of the simulation window (inclusive). ``None``
            means start at the beginning of the available data. Only used by
            ``Backtester.run`` (which slices the raw OHLCV frame before
            generating signals); ``run_from_signals`` does not re-slice.
        end_date: Last date of the simulation window (inclusive). ``None``
            means run to the end of the available data.
        next_day_open_fills: If True (v1 default and only supported mode),
            orders generated from day T signals fill at day T+1's open.
            ``False`` is not implemented and raises ``NotImplementedError``.
        slippage_pct: Slippage applied to every fill, as a fraction of price
            (0.0005 == 0.05%), always in the adverse direction: buys fill at
            ``price * (1 + slippage_pct)``, sells fill at
            ``price * (1 - slippage_pct)``.
        transaction_cost_pct: Transaction cost applied to every fill, as a
            fraction of notional (0.0005 == 0.05%), charged on both the entry
            and the exit leg of a trade.
        max_allocation_pct: Maximum fraction of current equity (cash, since
            at most one position is open at a time) that may be committed to
            a single trade (0.10 == 10%).

    A strategy definition's optional ``costs`` object
    (``{"transaction_cost_pct": ..., "slippage_pct": ...}``, see
    docs/strategy-format.md) overrides ``transaction_cost_pct`` /
    ``slippage_pct`` for that run when present. ``max_allocation_pct`` is not
    overridable at the strategy level.
    """

    initial_capital: float = 1_000_000.0
    start_date: date | None = None
    end_date: date | None = None
    next_day_open_fills: bool = True
    slippage_pct: float = 0.0005
    transaction_cost_pct: float = 0.0005
    max_allocation_pct: float = 0.10


@dataclass
class BacktestResult:
    """Full metrics set produced by a backtest run (project contract).

    All metric fields are computed by deterministic functions in
    ``quant_engine.metrics`` (via ``metrics.compute_all``) -- ``Backtester``
    never inlines metric math. ``equity_curve`` and ``trades`` are the
    artifacts persisted alongside a backtest run.

    Attributes:
        total_return: Total return over the simulation, as a fraction
            (0.25 == +25%).
        cagr: Compound annual growth rate, as a fraction.
        max_drawdown: Maximum peak-to-trough drawdown, as a positive fraction
            (0.20 == a 20% drawdown).
        win_rate: Fraction of closed trades with positive PnL, in [0, 1].
        avg_win: Average PnL of winning trades, in INR.
        avg_loss: Average PnL of losing trades, in INR (negative).
        profit_factor: Gross profit divided by gross loss (absolute value).
        num_trades: Number of closed round-trip trades.
        exposure_time: Fraction of bars with at least one open position,
            in [0, 1].
        sharpe: Sharpe-like ratio: annualized mean of daily returns divided by
            annualized standard deviation of daily returns (risk-free rate
            assumed 0 in v1).
        best_trade: PnL of the best single trade, in INR.
        worst_trade: PnL of the worst single trade, in INR.
        starting_capital: Equity at the start of the simulation, in INR
            (equal to ``BacktestConfig.initial_capital`` for the run).
        final_equity: Equity at the end of the simulation, in INR, after any
            end-of-data forced close of an open position.
        equity_curve: Daily equity curve artifact -- DataFrame with columns
            ``[date, equity]``. ``None`` until populated by a run.
        trades: Trade list artifact -- one dict per closed trade (symbol,
            entry/exit date and price, quantity, pnl, ...).
    """

    total_return: float
    cagr: float
    max_drawdown: float
    win_rate: float
    avg_win: float
    avg_loss: float
    profit_factor: float
    num_trades: int
    exposure_time: float
    sharpe: float
    best_trade: float
    worst_trade: float
    starting_capital: float
    final_equity: float
    equity_curve: pd.DataFrame | None = None
    trades: list[dict] = field(default_factory=list)


def _missing_columns(df: pd.DataFrame, required: list[str]) -> list[str]:
    return [c for c in required if c not in df.columns]


class Backtester:
    """Deterministic daily backtester for long-only strategies.

    ``run`` is the strategy-rules entry point (validates and slices raw OHLCV
    data, generates signals via ``quant_engine.signals.generate_signals``,
    then delegates). ``run_from_signals`` contains the entire simulation and
    can be driven directly with a hand-built signal frame -- this is the
    method exercised by ``tests/test_backtest.py`` so that backtest-engine
    tests have zero dependency on the signals interpreter.
    """

    def __init__(self, config: BacktestConfig | None = None) -> None:
        self.config: BacktestConfig = config if config is not None else BacktestConfig()

    def _ensure_next_day_open_fills(self) -> None:
        if not self.config.next_day_open_fills:
            raise NotImplementedError(
                "BacktestConfig.next_day_open_fills=False is not supported in v1; "
                "only next-day-open fills are implemented."
            )

    def run(self, df: pd.DataFrame, rules: dict, symbol: str = "") -> "BacktestResult":
        """Run a backtest of ``rules`` over OHLCV data.

        Args:
            df: OHLCV DataFrame satisfying the data-connector contract
                (columns ``[date, open, high, low, close, volume]``,
                ascending date, tz-naive, no duplicate dates, no NaN rows).
            rules: Strategy rules dict per docs/strategy-format.md; signals
                are generated via ``quant_engine.signals.generate_signals``.
            symbol: Optional symbol label to attach to trade records. If
                empty, resolved from ``rules["universe"]`` (see
                ``run_from_signals``).

        Returns:
            A fully populated :class:`BacktestResult`.

        Raises:
            ValueError: If ``df`` is missing required OHLCV columns or is
                empty (after slicing to the configured date window).
            NotImplementedError: If ``self.config.next_day_open_fills`` is
                False.
        """
        self._ensure_next_day_open_fills()

        missing = _missing_columns(df, _BASE_OHLCV_COLUMNS)
        if missing:
            raise ValueError(f"df is missing required OHLCV columns: {missing}")
        if len(df) == 0:
            raise ValueError("df must not be empty")

        sliced = df
        if self.config.start_date is not None or self.config.end_date is not None:
            dates = pd.to_datetime(df["date"])
            mask = pd.Series(True, index=df.index)
            if self.config.start_date is not None:
                mask &= dates >= pd.Timestamp(self.config.start_date)
            if self.config.end_date is not None:
                mask &= dates <= pd.Timestamp(self.config.end_date)
            sliced = df.loc[mask].reset_index(drop=True)

        if len(sliced) == 0:
            raise ValueError("df has no rows within the configured date window")

        signals_df = signals.generate_signals(sliced, rules)
        return self.run_from_signals(signals_df, rules, symbol=symbol)

    def run_from_signals(
        self, signals_df: pd.DataFrame, rules: dict, symbol: str = ""
    ) -> "BacktestResult":
        """Simulate a long-only backtest from a pre-built signal frame.

        This method contains ALL simulation logic and trusts its inputs: it
        does not validate ``rules`` against the strategy-format schema (that
        is the signals interpreter's job) -- it only reads the specific keys
        it needs (``stop_loss``, ``position_sizing``, ``max_holding_days``,
        ``costs``, ``universe``), and only when an entry is actually
        attempted (so a minimal ``rules`` dict is fine for signal frames that
        never fire an entry).

        Args:
            signals_df: A copy of an OHLCV frame with added boolean columns
                ``entry_signal`` / ``exit_signal`` (no NaN) and a
                ``stop_loss_price`` column (ignored -- see below), ascending
                date, tz-naive, no duplicate dates, no NaN OHLCV rows. Any
                extra indicator columns are ignored.
            rules: Strategy rules dict per docs/strategy-format.md.
            symbol: Optional symbol label for trade records. If empty,
                resolved from ``rules.get("universe")``: the sole element if
                the universe has exactly one symbol, else ``"?"``.

        Simulation semantics (exact, hand-checkable; see backtest.py's
        module docstring for the cost/slippage model):
            - Entry: ``entry_signal`` True on bar t, flat, and no exit
              pending -> buy at bar t+1's open, fill price
              ``open[t+1] * (1 + slippage_pct)``. Ignored on the last bar
              (no next open) and while a position is open.
            - Stop price = ``entry_fill_price * (1 - stop_loss.value)``,
              fixed for the life of the trade (recomputed from the actual
              fill; the indicative ``stop_loss_price`` column is ignored).
            - Position size = ``min(qty_risk, qty_alloc, qty_cash)``, all
              floored to whole shares:
                ``qty_risk = (position_sizing.value * equity) /
                (entry_fill_price * stop_loss.value)``;
                ``qty_alloc = (max_allocation_pct * equity) /
                entry_fill_price``;
                ``qty_cash =`` the largest quantity whose notional plus entry
                transaction cost fits in available cash. ``equity`` is cash
                at fill time (the account is flat immediately before an
                entry). ``qty < 1`` means no trade that bar (skip, stay
                flat).
            - Exits are evaluated per bar, in order, for an open position:
              (a) a next-open exit scheduled by bar t-1 (``exit_signal`` or
              the max-holding rule) fills at ``open[t] * (1 - slippage_pct)``;
              (b) failing that, an intraday stop check on bar t: gap-down
              (``open[t] <= stop_price``) fills at
              ``open[t] * (1 - slippage_pct)``, else a low-pierce
              (``low[t] <= stop_price``) fills at
              ``stop_price * (1 - slippage_pct)`` -- this may fire on the
              entry bar itself; (c) failing that, if ``max_holding_days`` is
              set and the position has been held that many bars as of bar
              t's close (entry bar counted as day 1), a ``"max_holding"``
              exit is scheduled for bar t+1's open; (d) failing that, if
              ``exit_signal`` is True on bar t, a ``"signal"`` exit is
              scheduled for bar t+1's open.
            - Every fill (entry or exit) is charged
              ``transaction_cost_pct`` of its notional.
            - End of data: a position still open after the last bar is
              force-closed at ``close[last] * (1 - slippage_pct)`` (plus
              transaction cost), reason ``"end_of_data"`` -- a documented v1
              simplification so metrics always reflect fully realized
              trades. The equity curve's final point is overwritten with the
              post-force-close cash so it, too, reflects the realized
              outcome.
            - Equity is marked to market at every bar's close:
              ``equity[t] = cash + qty * close[t]``.
            - Dates in ``trades`` and the equity curve are taken as-is from
              ``signals_df["date"]`` (no type conversion); be consistent with
              whatever dtype the caller's frame uses (typically
              ``pandas.Timestamp``).

        Returns:
            A fully populated :class:`BacktestResult`.

        Raises:
            ValueError: If ``signals_df`` is missing required columns or is
                empty.
            NotImplementedError: If ``self.config.next_day_open_fills`` is
                False.
        """
        self._ensure_next_day_open_fills()

        missing = _missing_columns(signals_df, _SIGNAL_FRAME_COLUMNS)
        if missing:
            raise ValueError(f"signals_df is missing required columns: {missing}")
        if len(signals_df) == 0:
            raise ValueError("signals_df must not be empty")

        frame = signals_df.reset_index(drop=True)
        n = len(frame)

        dates = frame["date"]
        opens = frame["open"]
        lows = frame["low"]
        closes = frame["close"]
        entry_signals = frame["entry_signal"]
        exit_signals = frame["exit_signal"]

        if symbol:
            resolved_symbol = symbol
        else:
            universe = rules.get("universe") or []
            resolved_symbol = universe[0] if len(universe) == 1 else "?"

        costs = rules.get("costs") or {}
        transaction_cost_pct = float(costs.get("transaction_cost_pct", self.config.transaction_cost_pct))
        slippage_pct = float(costs.get("slippage_pct", self.config.slippage_pct))
        max_allocation_pct = self.config.max_allocation_pct

        max_holding_days = rules.get("max_holding_days")

        # -- simulation state -------------------------------------------------
        cash = self.config.initial_capital
        qty = 0
        entry_price: float | None = None
        entry_date: Any = None
        entry_bar_index: int | None = None
        entry_cost: float | None = None
        stop_price: float | None = None

        pending_exit_reason: str | None = None
        pending_entry = False

        trades: list[dict] = []
        equity_rows: list[dict] = []
        position_flags: list[bool] = []

        def close_position(exit_date: Any, exit_fill: float, reason: str, held_through_bar: int) -> None:
            nonlocal cash, qty, entry_price, entry_date, entry_bar_index, entry_cost, stop_price
            exit_cost = qty * exit_fill * transaction_cost_pct
            cash += qty * exit_fill - exit_cost
            pnl = qty * (exit_fill - entry_price) - entry_cost - exit_cost
            notional = entry_price * qty
            return_pct = pnl / notional if notional != 0 else 0.0
            holding_days = held_through_bar - entry_bar_index + 1
            trades.append(
                {
                    "symbol": resolved_symbol,
                    "entry_date": entry_date,
                    "entry_price": entry_price,
                    "exit_date": exit_date,
                    "exit_price": exit_fill,
                    "quantity": qty,
                    "pnl": pnl,
                    "return_pct": return_pct,
                    "holding_days": holding_days,
                    "exit_reason": reason,
                    "entry_cost": entry_cost,
                    "exit_cost": exit_cost,
                }
            )
            qty = 0
            entry_price = None
            entry_date = None
            entry_bar_index = None
            entry_cost = None
            stop_price = None

        eps = 1e-9

        for i in range(n):
            open_i = float(opens.iat[i])
            low_i = float(lows.iat[i])
            close_i = float(closes.iat[i])
            date_i = dates.iat[i]

            # (a) scheduled next-open exit from bar i-1 (signal / max_holding)
            if qty > 0 and pending_exit_reason is not None:
                exit_fill = open_i * (1.0 - slippage_pct)
                close_position(date_i, exit_fill, pending_exit_reason, held_through_bar=i - 1)
                pending_exit_reason = None

            # scheduled entry from bar i-1 (entry_signal & flat & no exit pending)
            attempt_entry = pending_entry
            pending_entry = False
            if qty == 0 and attempt_entry:
                stop_loss_cfg = rules.get("stop_loss", {})
                sizing_cfg = rules.get("position_sizing", {})
                stop_value = float(stop_loss_cfg["value"])
                sizing_value = float(sizing_cfg["value"])

                fill_price = open_i * (1.0 + slippage_pct)
                equity = cash  # flat immediately before this fill

                per_share_risk = fill_price * stop_value
                qty_risk = (
                    math.floor((sizing_value * equity) / per_share_risk + eps)
                    if per_share_risk > 0
                    else 0
                )
                qty_alloc = (
                    math.floor((max_allocation_pct * equity) / fill_price + eps)
                    if fill_price > 0
                    else 0
                )
                denom = fill_price * (1.0 + transaction_cost_pct)
                qty_cash = math.floor(cash / denom + eps) if denom > 0 else 0

                qty_to_buy = min(qty_risk, qty_alloc, qty_cash)

                if qty_to_buy >= 1:
                    fill_cost = qty_to_buy * fill_price * transaction_cost_pct
                    cash -= qty_to_buy * fill_price + fill_cost
                    qty = qty_to_buy
                    entry_price = fill_price
                    entry_date = date_i
                    entry_bar_index = i
                    entry_cost = fill_cost
                    stop_price = fill_price * (1.0 - stop_value)

            # (b) intraday stop check
            if qty > 0:
                if open_i <= stop_price:
                    exit_fill = open_i * (1.0 - slippage_pct)
                    close_position(date_i, exit_fill, "stop_loss", held_through_bar=i)
                elif low_i <= stop_price:
                    exit_fill = stop_price * (1.0 - slippage_pct)
                    close_position(date_i, exit_fill, "stop_loss", held_through_bar=i)

            # (c) max-holding-days check
            if qty > 0 and pending_exit_reason is None and max_holding_days:
                holding_days_so_far = i - entry_bar_index + 1
                if holding_days_so_far >= int(max_holding_days):
                    pending_exit_reason = "max_holding"

            # (d) exit_signal check
            if qty > 0 and pending_exit_reason is None and bool(exit_signals.iat[i]):
                pending_exit_reason = "signal"

            equity_i = cash + qty * close_i
            equity_rows.append({"date": date_i, "equity": equity_i})
            position_flags.append(qty > 0)

            # schedule entry for bar i+1, based on bar i's own state
            if i < n - 1 and qty == 0 and pending_exit_reason is None and bool(entry_signals.iat[i]):
                pending_entry = True

        # end-of-data forced close
        if qty > 0:
            last_close = float(closes.iat[n - 1])
            exit_fill = last_close * (1.0 - slippage_pct)
            close_position(dates.iat[n - 1], exit_fill, "end_of_data", held_through_bar=n - 1)
            equity_rows[-1]["equity"] = cash

        equity_curve = pd.DataFrame(equity_rows, columns=["date", "equity"])
        equity_series = equity_curve["equity"]
        position_flags_series = pd.Series(position_flags, dtype=bool)

        computed = metrics.compute_all(equity_series, trades, position_flags_series)
        final_equity = float(equity_series.iloc[-1])

        return BacktestResult(
            **computed,
            starting_capital=self.config.initial_capital,
            final_equity=final_equity,
            equity_curve=equity_curve,
            trades=trades,
        )
