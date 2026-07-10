"""Tests for quant_engine.backtest.

Drives ``Backtester.run_from_signals`` directly with hand-built signal frames
(``make_frame``) so these tests have zero dependency on the signals
interpreter (implemented separately). Expected fill prices / costs / pnl are
computed via the exact formulas documented on ``run_from_signals`` (plain
Python arithmetic, not calls into the implementation), so each assertion
checks the math.

Cost model reminder (defaults): ``slippage_pct=0.0005``,
``transaction_cost_pct=0.0005``, ``max_allocation_pct=0.10``,
``initial_capital=1_000_000.0``.
"""

from __future__ import annotations

import pandas as pd
import pytest

from quant_engine.backtest import Backtester, BacktestConfig

SLIP = 0.0005
TXN = 0.0005


def make_frame(
    opens: list[float],
    highs: list[float],
    lows: list[float],
    closes: list[float],
    entry_signal: list[bool] | None = None,
    exit_signal: list[bool] | None = None,
    volumes: list[float] | None = None,
    stop_loss_price: list[float] | None = None,
    start: str = "2024-01-01",
) -> pd.DataFrame:
    """Build a minimal signal frame (OHLCV + entry/exit/stop_loss_price)."""
    n = len(opens)
    assert len(highs) == len(lows) == len(closes) == n
    dates = pd.date_range(start, periods=n, freq="D")
    return pd.DataFrame(
        {
            "date": dates,
            "open": [float(x) for x in opens],
            "high": [float(x) for x in highs],
            "low": [float(x) for x in lows],
            "close": [float(x) for x in closes],
            "volume": volumes if volumes is not None else [1_000_000.0] * n,
            "entry_signal": entry_signal if entry_signal is not None else [False] * n,
            "exit_signal": exit_signal if exit_signal is not None else [False] * n,
            "stop_loss_price": stop_loss_price if stop_loss_price is not None else [0.0] * n,
        }
    )


def rules(stop_value: float = 0.05, sizing_value: float = 0.01, **extra) -> dict:
    r = {
        "universe": ["TEST"],
        "stop_loss": {"type": "percent", "value": stop_value},
        "position_sizing": {"type": "risk_percent", "value": sizing_value},
    }
    r.update(extra)
    return r


# --------------------------------------------------------------------------
# (1) simple entry -> signal exit round trip (fully hand-verified)
# --------------------------------------------------------------------------


def test_simple_entry_and_signal_exit_round_trip() -> None:
    frame = make_frame(
        opens=[100.0, 100.0, 120.0, 125.0],
        highs=[101.0, 103.0, 121.0, 126.0],
        lows=[99.0, 108.0, 119.0, 124.0],
        closes=[100.0, 111.0, 120.0, 125.0],
        entry_signal=[True, False, False, False],
        exit_signal=[False, True, False, False],
    )
    bt = Backtester()
    result = bt.run_from_signals(frame, rules(stop_value=0.5, sizing_value=0.01))

    # Entry fills at bar1's open with slippage; sizing is risk-bound.
    entry_fill = 100.0 * (1 + SLIP)
    assert entry_fill == pytest.approx(100.05)
    per_share_risk = entry_fill * 0.5
    qty_risk = int(0.01 * 1_000_000.0 // per_share_risk)  # floor, exact division here
    assert qty_risk == 199

    exit_fill = 120.0 * (1 - SLIP)
    entry_cost = qty_risk * entry_fill * TXN
    exit_cost = qty_risk * exit_fill * TXN
    expected_pnl = qty_risk * (exit_fill - entry_fill) - entry_cost - exit_cost

    assert result.num_trades == 1
    trade = result.trades[0]
    assert trade["quantity"] == qty_risk
    assert trade["entry_price"] == pytest.approx(entry_fill)
    assert trade["exit_price"] == pytest.approx(exit_fill)
    assert trade["entry_cost"] == pytest.approx(entry_cost)
    assert trade["exit_cost"] == pytest.approx(exit_cost)
    assert trade["pnl"] == pytest.approx(expected_pnl)
    assert trade["exit_reason"] == "signal"
    assert trade["holding_days"] == 1

    # cash/equity arithmetic by hand:
    cash_after_entry = 1_000_000.0 - qty_risk * entry_fill - entry_cost
    cash_after_exit = cash_after_entry + qty_risk * exit_fill - exit_cost
    assert cash_after_exit == pytest.approx(1_000_000.0 + expected_pnl)
    assert result.final_equity == pytest.approx(cash_after_exit)
    assert result.starting_capital == 1_000_000.0

    eq = result.equity_curve["equity"].tolist()
    assert eq[0] == pytest.approx(1_000_000.0)  # flat first bar
    assert eq[1] == pytest.approx(cash_after_entry + qty_risk * 111.0)
    assert eq[2] == pytest.approx(cash_after_exit)
    assert eq[3] == pytest.approx(cash_after_exit)  # flat afterwards


# --------------------------------------------------------------------------
# (2) stop-loss intraday low-pierce trigger
# --------------------------------------------------------------------------


def test_stop_loss_intraday_low_pierce() -> None:
    frame = make_frame(
        opens=[100.0, 100.0, 97.0, 96.0],
        highs=[101.0, 103.0, 98.0, 97.0],
        lows=[99.0, 98.0, 94.0, 95.0],
        closes=[100.0, 102.0, 95.0, 96.0],
        entry_signal=[True, False, False, False],
    )
    bt = Backtester()
    result = bt.run_from_signals(frame, rules(stop_value=0.05, sizing_value=0.01))

    entry_fill = 100.0 * (1 + SLIP)
    stop_price = entry_fill * (1 - 0.05)
    assert stop_price == pytest.approx(95.0475)
    # bar2 (i=2): open=97 > stop (no gap), low=94 <= stop -> low-pierce
    exit_fill = stop_price * (1 - SLIP)

    trade = result.trades[0]
    assert trade["exit_reason"] == "stop_loss"
    assert trade["exit_price"] == pytest.approx(exit_fill)
    assert trade["holding_days"] == 2  # entry bar=1, stop bar=2


# --------------------------------------------------------------------------
# (3) gap-down stop trigger
# --------------------------------------------------------------------------


def test_stop_loss_gap_down() -> None:
    frame = make_frame(
        opens=[100.0, 100.0, 90.0],
        highs=[101.0, 103.0, 92.0],
        lows=[99.0, 98.0, 89.0],
        closes=[100.0, 101.0, 91.0],
        entry_signal=[True, False, False],
    )
    bt = Backtester()
    result = bt.run_from_signals(frame, rules(stop_value=0.05, sizing_value=0.01))

    entry_fill = 100.0 * (1 + SLIP)
    stop_price = entry_fill * (1 - 0.05)
    assert 90.0 <= stop_price  # open_2 <= stop_price -> gap down
    exit_fill = 90.0 * (1 - SLIP)  # gap-down fills at bar's open, not stop_price

    trade = result.trades[0]
    assert trade["exit_reason"] == "stop_loss"
    assert trade["exit_price"] == pytest.approx(exit_fill)
    assert trade["holding_days"] == 2


# --------------------------------------------------------------------------
# (4) stop triggers on the entry fill bar itself
# --------------------------------------------------------------------------


def test_stop_loss_on_entry_bar_itself() -> None:
    frame = make_frame(
        opens=[100.0, 100.0, 90.0],
        highs=[101.0, 103.0, 95.0],
        lows=[99.0, 94.0, 88.0],
        closes=[100.0, 96.0, 92.0],
        entry_signal=[True, False, False],
    )
    bt = Backtester()
    result = bt.run_from_signals(frame, rules(stop_value=0.05, sizing_value=0.01))

    entry_fill = 100.0 * (1 + SLIP)
    stop_price = entry_fill * (1 - 0.05)
    exit_fill = stop_price * (1 - SLIP)

    assert result.num_trades == 1
    trade = result.trades[0]
    assert trade["entry_date"] == trade["exit_date"]  # same bar
    assert trade["exit_reason"] == "stop_loss"
    assert trade["exit_price"] == pytest.approx(exit_fill)
    assert trade["holding_days"] == 1


# --------------------------------------------------------------------------
# (5) max_holding_days exit at the correct bar / reason
# --------------------------------------------------------------------------


def test_max_holding_days_exit() -> None:
    frame = make_frame(
        opens=[100.0, 100.0, 101.0, 105.0],
        highs=[101.0, 103.0, 104.0, 106.0],
        lows=[99.0, 97.0, 98.0, 104.0],
        closes=[100.0, 101.0, 102.0, 105.0],
        entry_signal=[True, False, False, False],
    )
    bt = Backtester()
    result = bt.run_from_signals(
        frame, rules(stop_value=0.05, sizing_value=0.01, max_holding_days=2)
    )

    entry_fill = 100.0 * (1 + SLIP)
    exit_fill = 105.0 * (1 - SLIP)

    assert result.num_trades == 1
    trade = result.trades[0]
    assert trade["exit_reason"] == "max_holding"
    assert trade["entry_price"] == pytest.approx(entry_fill)
    assert trade["exit_price"] == pytest.approx(exit_fill)
    assert trade["holding_days"] == 2
    assert str(trade["exit_date"].date()) == "2024-01-04"


# --------------------------------------------------------------------------
# (6) transaction-cost impact
# --------------------------------------------------------------------------


def test_transaction_cost_impact_changes_pnl_by_costs() -> None:
    frame = make_frame(
        opens=[100.0, 100.0, 120.0, 125.0],
        highs=[101.0, 103.0, 121.0, 126.0],
        lows=[99.0, 108.0, 119.0, 124.0],
        closes=[100.0, 111.0, 120.0, 125.0],
        entry_signal=[True, False, False, False],
        exit_signal=[False, True, False, False],
    )
    bt = Backtester()
    base_rules = rules(stop_value=0.5, sizing_value=0.01)

    with_cost = bt.run_from_signals(frame, base_rules)
    no_cost_rules = rules(
        stop_value=0.5, sizing_value=0.01, costs={"transaction_cost_pct": 0.0}
    )
    without_cost = bt.run_from_signals(frame, no_cost_rules)

    trade_with = with_cost.trades[0]
    trade_without = without_cost.trades[0]

    # Same quantity (risk-bound, unaffected by transaction cost) and fills
    # (slippage unchanged), so the only difference is transaction cost.
    assert trade_with["quantity"] == trade_without["quantity"]
    assert trade_without["entry_cost"] == 0.0
    assert trade_without["exit_cost"] == 0.0
    diff = trade_without["pnl"] - trade_with["pnl"]
    assert diff == pytest.approx(trade_with["entry_cost"] + trade_with["exit_cost"])


# --------------------------------------------------------------------------
# (7) slippage impact
# --------------------------------------------------------------------------


def test_slippage_impact_changes_fills() -> None:
    frame = make_frame(
        opens=[100.0, 100.0, 120.0, 125.0],
        highs=[101.0, 103.0, 121.0, 126.0],
        lows=[99.0, 108.0, 119.0, 124.0],
        closes=[100.0, 111.0, 120.0, 125.0],
        entry_signal=[True, False, False, False],
        exit_signal=[False, True, False, False],
    )
    bt = Backtester()
    base_rules = rules(stop_value=0.5, sizing_value=0.01)

    with_slip = bt.run_from_signals(frame, base_rules)
    no_slip_rules = rules(stop_value=0.5, sizing_value=0.01, costs={"slippage_pct": 0.0})
    without_slip = bt.run_from_signals(frame, no_slip_rules)

    assert with_slip.trades[0]["entry_price"] == pytest.approx(100.0 * (1 + SLIP))
    assert without_slip.trades[0]["entry_price"] == pytest.approx(100.0)
    assert with_slip.trades[0]["exit_price"] == pytest.approx(120.0 * (1 - SLIP))
    assert without_slip.trades[0]["exit_price"] == pytest.approx(120.0)


# --------------------------------------------------------------------------
# (8) position sizing: each of the three constraints binds; qty < 1 -> no trade
# --------------------------------------------------------------------------


def test_sizing_risk_bound() -> None:
    frame = make_frame(
        opens=[100.0, 100.0, 100.0],
        highs=[101.0, 103.0, 103.0],
        lows=[99.0, 98.0, 98.0],
        closes=[100.0, 100.0, 100.0],
        entry_signal=[True, False, False],
    )
    bt = Backtester()  # defaults: max_allocation_pct=0.10, initial_capital=1e6
    result = bt.run_from_signals(frame, rules(stop_value=0.05, sizing_value=0.001))

    entry_fill = 100.0 * (1 + SLIP)
    per_share_risk = entry_fill * 0.05
    qty_risk = int((0.001 * 1_000_000.0) // per_share_risk)
    qty_alloc = int((0.10 * 1_000_000.0) // entry_fill)
    assert qty_risk < qty_alloc  # confirm risk is the binding constraint
    assert result.trades[0]["quantity"] == qty_risk


def test_sizing_allocation_bound() -> None:
    frame = make_frame(
        opens=[100.0, 100.0, 100.0],
        highs=[101.0, 103.0, 103.0],
        lows=[99.0, 98.0, 98.0],
        closes=[100.0, 100.0, 100.0],
        entry_signal=[True, False, False],
    )
    bt = Backtester()  # defaults: max_allocation_pct=0.10
    result = bt.run_from_signals(frame, rules(stop_value=0.05, sizing_value=0.5))

    entry_fill = 100.0 * (1 + SLIP)
    per_share_risk = entry_fill * 0.05
    qty_risk = int((0.5 * 1_000_000.0) // per_share_risk)
    qty_alloc = int((0.10 * 1_000_000.0) // entry_fill)
    assert qty_alloc < qty_risk  # confirm allocation is the binding constraint
    assert result.trades[0]["quantity"] == qty_alloc


def test_sizing_cash_bound() -> None:
    frame = make_frame(
        opens=[100.0, 100.0, 100.0],
        highs=[101.0, 103.0, 103.0],
        lows=[99.0, 98.0, 98.0],
        closes=[100.0, 100.0, 100.0],
        entry_signal=[True, False, False],
    )
    config = BacktestConfig(initial_capital=10_000.0, max_allocation_pct=10.0)
    bt = Backtester(config)
    result = bt.run_from_signals(frame, rules(stop_value=0.05, sizing_value=1.0))

    entry_fill = 100.0 * (1 + SLIP)
    denom = entry_fill * (1 + TXN)
    qty_cash = int(10_000.0 // denom)
    per_share_risk = entry_fill * 0.05
    qty_risk = int((1.0 * 10_000.0) // per_share_risk)
    qty_alloc = int((10.0 * 10_000.0) // entry_fill)
    assert qty_cash < qty_risk and qty_cash < qty_alloc  # cash is the binding constraint
    assert result.trades[0]["quantity"] == qty_cash


def test_sizing_below_one_share_skips_trade() -> None:
    frame = make_frame(
        opens=[100.0, 100.0, 100.0],
        highs=[101.0, 103.0, 103.0],
        lows=[99.0, 98.0, 98.0],
        closes=[100.0, 100.0, 100.0],
        entry_signal=[True, False, False],
    )
    config = BacktestConfig(initial_capital=50.0)  # not enough cash for 1 share at ~100
    bt = Backtester(config)
    result = bt.run_from_signals(frame, rules(stop_value=0.05, sizing_value=1.0))

    assert result.num_trades == 0
    assert result.equity_curve["equity"].tolist() == pytest.approx([50.0, 50.0, 50.0])


# --------------------------------------------------------------------------
# (9) no signals: flat equity curve, zero-trade metrics
# --------------------------------------------------------------------------


def test_no_signals_flat_equity_and_zero_trade_metrics() -> None:
    frame = make_frame(
        opens=[100.0, 105.0, 95.0, 110.0],
        highs=[102.0, 107.0, 97.0, 112.0],
        lows=[98.0, 103.0, 93.0, 108.0],
        closes=[101.0, 106.0, 96.0, 111.0],
    )
    bt = Backtester()
    result = bt.run_from_signals(frame, rules={})

    assert result.num_trades == 0
    assert result.equity_curve["equity"].tolist() == pytest.approx([1_000_000.0] * 4)
    assert result.win_rate == 0.0
    assert result.avg_win == 0.0
    assert result.avg_loss == 0.0
    assert result.profit_factor == 0.0
    assert result.best_trade == 0.0
    assert result.worst_trade == 0.0
    assert result.sharpe == 0.0
    assert result.exposure_time == 0.0
    assert result.starting_capital == 1_000_000.0
    assert result.final_equity == 1_000_000.0


# --------------------------------------------------------------------------
# (10) entry signal on the last bar is ignored
# --------------------------------------------------------------------------


def test_entry_signal_on_last_bar_is_ignored() -> None:
    frame = make_frame(
        opens=[100.0, 105.0, 95.0, 110.0],
        highs=[102.0, 107.0, 97.0, 112.0],
        lows=[98.0, 103.0, 93.0, 108.0],
        closes=[101.0, 106.0, 96.0, 111.0],
        entry_signal=[False, False, False, True],
    )
    bt = Backtester()
    result = bt.run_from_signals(frame, rules(stop_value=0.05, sizing_value=0.01))

    assert result.num_trades == 0
    assert result.equity_curve["equity"].tolist() == pytest.approx([1_000_000.0] * 4)


# --------------------------------------------------------------------------
# (11) end-of-data forced close
# --------------------------------------------------------------------------


def test_end_of_data_forced_close() -> None:
    frame = make_frame(
        opens=[100.0, 100.0, 105.0, 110.0],
        highs=[101.0, 103.0, 106.0, 112.0],
        lows=[99.0, 97.0, 104.0, 108.0],
        closes=[100.0, 101.0, 105.0, 111.0],
        entry_signal=[True, False, False, False],
    )
    bt = Backtester()
    result = bt.run_from_signals(frame, rules(stop_value=0.5, sizing_value=0.01))

    entry_fill = 100.0 * (1 + SLIP)
    exit_fill = 111.0 * (1 - SLIP)  # forced close at LAST bar's close, not open

    assert result.num_trades == 1
    trade = result.trades[0]
    assert trade["exit_reason"] == "end_of_data"
    assert trade["entry_price"] == pytest.approx(entry_fill)
    assert trade["exit_price"] == pytest.approx(exit_fill)
    assert trade["holding_days"] == 3  # bars 1,2,3 (entry bar counted as day 1)

    qty = trade["quantity"]
    exit_cost = qty * exit_fill * TXN
    entry_cost = trade["entry_cost"]
    cash_after_entry = 1_000_000.0 - qty * entry_fill - entry_cost
    expected_final_cash = cash_after_entry + qty * exit_fill - exit_cost

    assert result.final_equity == pytest.approx(expected_final_cash)
    # The equity curve's last point reflects the realized (post-force-close)
    # cash, not the naive mark-to-market value at the last close.
    naive_mtm = cash_after_entry + qty * 111.0
    assert result.equity_curve["equity"].iloc[-1] == pytest.approx(expected_final_cash)
    assert expected_final_cash != pytest.approx(naive_mtm)


# --------------------------------------------------------------------------
# (12) equity curve marks at close each bar
# --------------------------------------------------------------------------


def test_equity_curve_marks_at_close_each_bar() -> None:
    frame = make_frame(
        opens=[100.0, 100.0, 120.0, 125.0],
        highs=[101.0, 103.0, 121.0, 126.0],
        lows=[99.0, 108.0, 119.0, 124.0],
        closes=[100.0, 111.0, 120.0, 125.0],
        entry_signal=[True, False, False, False],
        exit_signal=[False, True, False, False],
    )
    bt = Backtester()
    result = bt.run_from_signals(frame, rules(stop_value=0.5, sizing_value=0.01))

    entry_fill = 100.0 * (1 + SLIP)
    qty = result.trades[0]["quantity"]
    entry_cost = result.trades[0]["entry_cost"]
    cash_after_entry = 1_000_000.0 - qty * entry_fill - entry_cost

    eq = result.equity_curve["equity"].tolist()
    assert eq[0] == pytest.approx(1_000_000.0)  # flat, marked at close[0]
    assert eq[1] == pytest.approx(cash_after_entry + qty * 111.0)  # marked at close[1]
    assert eq[2] == pytest.approx(result.final_equity)  # flat after exit
    assert eq[3] == pytest.approx(result.final_equity)


# --------------------------------------------------------------------------
# (13) trade list fields are complete and correct
# --------------------------------------------------------------------------


def test_trade_list_fields_complete() -> None:
    frame = make_frame(
        opens=[100.0, 100.0, 120.0, 125.0],
        highs=[101.0, 103.0, 121.0, 126.0],
        lows=[99.0, 108.0, 119.0, 124.0],
        closes=[100.0, 111.0, 120.0, 125.0],
        entry_signal=[True, False, False, False],
        exit_signal=[False, True, False, False],
    )
    bt = Backtester()
    result = bt.run_from_signals(frame, rules(stop_value=0.5, sizing_value=0.01))

    trade = result.trades[0]
    expected_keys = {
        "symbol",
        "entry_date",
        "entry_price",
        "exit_date",
        "exit_price",
        "quantity",
        "pnl",
        "return_pct",
        "holding_days",
        "exit_reason",
        "entry_cost",
        "exit_cost",
    }
    assert expected_keys <= set(trade.keys())
    assert trade["symbol"] == "TEST"  # resolved from rules["universe"][0]
    assert trade["exit_reason"] == "signal"
    assert trade["quantity"] > 0
    assert trade["return_pct"] == pytest.approx(
        trade["pnl"] / (trade["entry_price"] * trade["quantity"])
    )


def test_symbol_parameter_overrides_universe() -> None:
    frame = make_frame(
        opens=[100.0, 100.0, 120.0],
        highs=[101.0, 103.0, 121.0],
        lows=[99.0, 108.0, 119.0],
        closes=[100.0, 111.0, 120.0],
        entry_signal=[True, False, False],
        exit_signal=[False, True, False],
    )
    bt = Backtester()
    result = bt.run_from_signals(
        frame, rules(stop_value=0.5, sizing_value=0.01), symbol="OVERRIDE"
    )
    assert result.trades[0]["symbol"] == "OVERRIDE"


# --------------------------------------------------------------------------
# (14) exposure_time matches a hand count
# --------------------------------------------------------------------------


def test_exposure_time_matches_hand_count() -> None:
    frame = make_frame(
        opens=[100.0, 100.0, 120.0, 125.0],
        highs=[101.0, 103.0, 121.0, 126.0],
        lows=[99.0, 108.0, 119.0, 124.0],
        closes=[100.0, 111.0, 120.0, 125.0],
        entry_signal=[True, False, False, False],
        exit_signal=[False, True, False, False],
    )
    bt = Backtester()
    result = bt.run_from_signals(frame, rules(stop_value=0.5, sizing_value=0.01))

    # bar0: flat (entry not yet filled); bar1: holding; bar2: exit executes
    # before mark-to-market, so flat; bar3: flat. Open on 1 of 4 bars.
    assert result.exposure_time == pytest.approx(0.25)


# --------------------------------------------------------------------------
# (15) bad data raises ValueError
# --------------------------------------------------------------------------


def test_missing_column_raises_value_error() -> None:
    frame = make_frame(
        opens=[100.0, 101.0],
        highs=[102.0, 103.0],
        lows=[99.0, 100.0],
        closes=[101.0, 102.0],
    ).drop(columns=["volume"])
    bt = Backtester()
    with pytest.raises(ValueError):
        bt.run_from_signals(frame, rules={})


def test_empty_dataframe_raises_value_error() -> None:
    frame = make_frame(opens=[], highs=[], lows=[], closes=[])
    bt = Backtester()
    with pytest.raises(ValueError):
        bt.run_from_signals(frame, rules={})


# --------------------------------------------------------------------------
# (16) config validation: next_day_open_fills=False raises NotImplementedError
# --------------------------------------------------------------------------


def test_next_day_open_fills_false_raises_not_implemented() -> None:
    frame = make_frame(opens=[100.0], highs=[101.0], lows=[99.0], closes=[100.0])
    bt = Backtester(BacktestConfig(next_day_open_fills=False))
    with pytest.raises(NotImplementedError):
        bt.run_from_signals(frame, rules={})


# --------------------------------------------------------------------------
# (17) strategy-level costs override config costs
# --------------------------------------------------------------------------


def test_strategy_costs_override_config_costs() -> None:
    frame = make_frame(
        opens=[100.0, 100.0, 120.0],
        highs=[101.0, 103.0, 121.0],
        lows=[99.0, 108.0, 119.0],
        closes=[100.0, 111.0, 120.0],
        entry_signal=[True, False, False],
        exit_signal=[False, True, False],
    )
    bt = Backtester()  # config defaults: slippage 0.0005, txn cost 0.0005
    overridden = rules(
        stop_value=0.5,
        sizing_value=0.01,
        costs={"transaction_cost_pct": 0.01, "slippage_pct": 0.02},
    )
    result = bt.run_from_signals(frame, overridden)

    expected_entry_fill = 100.0 * (1 + 0.02)
    trade = result.trades[0]
    assert trade["entry_price"] == pytest.approx(expected_entry_fill)
    assert trade["entry_price"] != pytest.approx(100.0 * (1 + SLIP))
    expected_entry_cost = trade["quantity"] * expected_entry_fill * 0.01
    assert trade["entry_cost"] == pytest.approx(expected_entry_cost)
