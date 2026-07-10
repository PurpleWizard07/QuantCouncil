"""Foundation tests for quant_engine: importability, stub behavior, defaults."""

import pandas as pd
import pytest

import quant_engine
from quant_engine import backtest, indicators, metrics, signals
from quant_engine.backtest import BacktestConfig, Backtester, BacktestResult
from quant_engine.indicators import sma


def test_package_imports() -> None:
    assert quant_engine.__version__ == "0.1.0"
    assert indicators is not None
    assert signals is not None
    assert backtest is not None
    assert metrics is not None


def test_sma_smoke() -> None:
    # Phase 2 implemented sma(); full coverage lives in test_indicators.py.
    # This is a minimal smoke check that the import and basic call still work.
    series = pd.Series([1.0, 2.0, 3.0])
    result = sma(series, window=2)
    assert result.tolist() == pytest.approx([float("nan"), 1.5, 2.5], nan_ok=True)


def test_backtest_config_defaults_match_paper_rules() -> None:
    config = BacktestConfig()
    assert config.initial_capital == 1_000_000.0
    assert config.start_date is None
    assert config.end_date is None
    assert config.next_day_open_fills is True
    assert config.slippage_pct == 0.0005
    assert config.transaction_cost_pct == 0.0005
    assert config.max_allocation_pct == 0.10


def test_backtester_run_from_signals_empty_signals_is_no_trade_smoke() -> None:
    # Phase 3 implemented run_from_signals(); full coverage lives in
    # test_backtest.py. This is a minimal smoke check that an all-False
    # signal frame produces a flat equity curve and zero trades.
    backtester = Backtester()
    df = pd.DataFrame(
        {
            "date": pd.date_range("2024-01-01", periods=3, freq="D"),
            "open": [100.0, 101.0, 102.0],
            "high": [101.0, 102.0, 103.0],
            "low": [99.0, 100.0, 101.0],
            "close": [100.5, 101.5, 102.5],
            "volume": [1_000_000.0, 1_000_000.0, 1_000_000.0],
            "entry_signal": [False, False, False],
            "exit_signal": [False, False, False],
            "stop_loss_price": [0.0, 0.0, 0.0],
        }
    )
    result = backtester.run_from_signals(df, rules={})
    assert result.num_trades == 0
    assert result.equity_curve["equity"].tolist() == [1_000_000.0] * 3


def test_backtester_run_from_signals_empty_df_raises_value_error() -> None:
    backtester = Backtester()
    df = pd.DataFrame(
        columns=[
            "date",
            "open",
            "high",
            "low",
            "close",
            "volume",
            "entry_signal",
            "exit_signal",
            "stop_loss_price",
        ]
    )
    with pytest.raises(ValueError):
        backtester.run_from_signals(df, rules={})


def test_backtest_result_has_contract_metric_fields() -> None:
    contract_fields = {
        "total_return",
        "cagr",
        "max_drawdown",
        "win_rate",
        "avg_win",
        "avg_loss",
        "profit_factor",
        "num_trades",
        "exposure_time",
        "sharpe",
        "best_trade",
        "worst_trade",
        "equity_curve",
        "trades",
    }
    assert contract_fields <= set(BacktestResult.__dataclass_fields__.keys())
