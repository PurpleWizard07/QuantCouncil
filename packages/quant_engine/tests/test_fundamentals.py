"""Tests for quant_engine.fundamentals.

Expected values are hand-derived from small, explicit statement fixtures, so
each assertion checks the math (and the .info-vs-computed fallback rule),
not just re-running the implementation.
"""

from __future__ import annotations

import math

import pandas as pd
import pytest

from quant_engine import fundamentals as fnd


def _frame(periods: list[str], rows: dict[str, list[float]]) -> pd.DataFrame:
    """Build a frame shaped like yfinance's statement output (see fundamentals.py)."""
    columns = pd.to_datetime(periods)
    return pd.DataFrame(list(rows.values()), index=list(rows.keys()), columns=columns)


# --------------------------------------------------------------------------
# return_on_equity / return_on_assets
# --------------------------------------------------------------------------


def test_roe_prefers_info_value_when_present() -> None:
    income_stmt = _frame(["2025-03-31"], {"Net Income": [100.0]})
    balance_sheet = _frame(["2025-03-31"], {"Stockholders Equity": [1000.0]})
    roe = fnd.return_on_equity({"returnOnEquity": 0.5}, income_stmt, balance_sheet)
    assert roe == 0.5  # not 100/1000 == 0.1 -- info wins when present


def test_roe_falls_back_to_computed_value_when_info_missing() -> None:
    income_stmt = _frame(["2025-03-31"], {"Net Income": [100.0]})
    balance_sheet = _frame(["2025-03-31"], {"Stockholders Equity": [1000.0]})
    roe = fnd.return_on_equity({}, income_stmt, balance_sheet)
    assert roe == pytest.approx(0.1)


def test_roe_none_when_equity_row_missing() -> None:
    income_stmt = _frame(["2025-03-31"], {"Net Income": [100.0]})
    balance_sheet = _frame(["2025-03-31"], {"Total Assets": [1000.0]})  # no equity row
    assert fnd.return_on_equity({}, income_stmt, balance_sheet) is None


def test_roa_falls_back_to_computed_value_when_info_missing() -> None:
    income_stmt = _frame(["2025-03-31"], {"Net Income": [50.0]})
    balance_sheet = _frame(["2025-03-31"], {"Total Assets": [500.0]})
    assert fnd.return_on_assets({}, income_stmt, balance_sheet) == pytest.approx(0.1)


# --------------------------------------------------------------------------
# current_ratio / quick_ratio
# --------------------------------------------------------------------------


def test_current_ratio_normal_case() -> None:
    balance_sheet = _frame(
        ["2025-03-31"], {"Current Assets": [200.0], "Current Liabilities": [100.0]}
    )
    assert fnd.current_ratio(balance_sheet) == pytest.approx(2.0)


def test_current_ratio_none_for_unclassified_balance_sheet() -> None:
    # Banks report no Current Assets / Current Liabilities rows at all.
    balance_sheet = _frame(["2025-03-31"], {"Total Assets": [1000.0]})
    assert fnd.current_ratio(balance_sheet) is None


def test_current_ratio_none_when_liabilities_are_zero() -> None:
    balance_sheet = _frame(
        ["2025-03-31"], {"Current Assets": [200.0], "Current Liabilities": [0.0]}
    )
    assert fnd.current_ratio(balance_sheet) is None


def test_quick_ratio_subtracts_inventory() -> None:
    balance_sheet = _frame(
        ["2025-03-31"],
        {"Current Assets": [200.0], "Current Liabilities": [100.0], "Inventory": [50.0]},
    )
    assert fnd.quick_ratio(balance_sheet) == pytest.approx(1.5)


def test_quick_ratio_treats_missing_inventory_as_zero() -> None:
    # An IT-services company with no Inventory row -> quick ratio == current ratio.
    balance_sheet = _frame(
        ["2025-03-31"], {"Current Assets": [200.0], "Current Liabilities": [100.0]}
    )
    assert fnd.quick_ratio(balance_sheet) == pytest.approx(fnd.current_ratio(balance_sheet))


# --------------------------------------------------------------------------
# annual_history
# --------------------------------------------------------------------------


def test_annual_history_happy_path_newest_first() -> None:
    income_stmt = _frame(
        ["2025-03-31", "2024-03-31"], {"Total Revenue": [900.0, 800.0], "Net Income": [70.0, 60.0]}
    )
    balance_sheet = _frame(
        ["2025-03-31", "2024-03-31"], {"Total Assets": [1500.0, 1400.0]}
    )
    cashflow = _frame(["2025-03-31", "2024-03-31"], {"Operating Cash Flow": [120.0, 110.0]})

    rows = fnd.annual_history(income_stmt, balance_sheet, cashflow)

    assert len(rows) == 2
    assert rows[0]["fiscal_year_end"] == "2025-03-31"
    assert rows[0]["total_revenue"] == 900.0
    assert rows[0]["net_income"] == 70.0
    assert rows[0]["total_assets"] == 1500.0
    assert rows[0]["operating_cash_flow"] == 120.0
    assert rows[0]["total_liabilities"] is None  # never provided in this fixture
    assert rows[1]["fiscal_year_end"] == "2024-03-31"


def test_annual_history_handles_mismatched_period_counts_across_statements() -> None:
    # income_stmt has 2 years; balance_sheet only has 1 -- observed for real on
    # HDFCBANK (5 income-statement years, 4 balance-sheet years).
    income_stmt = _frame(
        ["2025-03-31", "2024-03-31"], {"Total Revenue": [900.0, 800.0]}
    )
    balance_sheet = _frame(["2025-03-31"], {"Total Assets": [1500.0]})

    rows = fnd.annual_history(income_stmt, balance_sheet, pd.DataFrame())

    assert rows[0]["total_assets"] == 1500.0
    assert rows[1]["total_assets"] is None  # 2024-03-31 column absent from balance_sheet


def test_annual_history_respects_limit() -> None:
    periods = ["2025-03-31", "2024-03-31", "2023-03-31"]
    income_stmt = _frame(periods, {"Total Revenue": [3.0, 2.0, 1.0]})
    rows = fnd.annual_history(income_stmt, pd.DataFrame(), pd.DataFrame(), limit=2)
    assert len(rows) == 2


def test_annual_history_empty_income_stmt_returns_empty_list() -> None:
    assert fnd.annual_history(pd.DataFrame(), pd.DataFrame(), pd.DataFrame()) == []


# --------------------------------------------------------------------------
# build_snapshot
# --------------------------------------------------------------------------


def test_build_snapshot_shape_and_values() -> None:
    info = {
        "longName": "Test Co Ltd",
        "sector": "Technology",
        "industry": "IT Services",
        "currency": "INR",
        "marketCap": 1_000_000.0,
        "trailingPE": 20.0,
        "trailingEps": 10.0,
        "dividendRate": 5.0,
        "dividendYield": 2.5,
        "profitMargins": 0.15,
        "revenueGrowth": 0.1,
        "debtToEquity": 9.5,
        "returnOnEquity": 0.32,
        "lastFiscalYearEnd": 1743379200,  # 2025-03-31 UTC
    }
    income_stmt = _frame(["2025-03-31"], {"Total Revenue": [900.0], "Net Income": [70.0]})
    balance_sheet = _frame(
        ["2025-03-31"],
        {"Current Assets": [200.0], "Current Liabilities": [100.0], "Stockholders Equity": [500.0]},
    )
    cashflow = _frame(["2025-03-31"], {"Operating Cash Flow": [120.0]})

    snapshot = fnd.build_snapshot(info, income_stmt, balance_sheet, cashflow)

    assert snapshot["profile"] == {
        "name": "Test Co Ltd",
        "sector": "Technology",
        "industry": "IT Services",
        "currency": "INR",
    }
    assert snapshot["valuation"]["market_cap"] == 1_000_000.0
    assert snapshot["valuation"]["trailing_pe"] == 20.0
    assert snapshot["per_share"]["trailing_eps"] == 10.0
    assert snapshot["dividends"]["dividend_yield_pct"] == 2.5
    assert snapshot["profitability"]["profit_margin"] == 0.15
    assert snapshot["profitability"]["return_on_equity"] == 0.32  # info wins
    assert snapshot["growth"]["revenue_growth"] == 0.1
    assert snapshot["financial_health"]["debt_to_equity_pct"] == 9.5
    assert snapshot["financial_health"]["current_ratio"] == pytest.approx(2.0)
    assert snapshot["annual_history"][0]["net_income"] == 70.0
    assert snapshot["as_of"]["last_fiscal_year_end"] == "2025-03-31"


def test_build_snapshot_missing_fields_are_none_not_nan() -> None:
    snapshot = fnd.build_snapshot({"longName": "Empty Co"}, pd.DataFrame(), pd.DataFrame(), pd.DataFrame())

    assert snapshot["valuation"]["trailing_pe"] is None
    assert snapshot["financial_health"]["current_ratio"] is None
    assert snapshot["annual_history"] == []
    assert snapshot["as_of"]["last_fiscal_year_end"] is None

    def _no_nan(value) -> bool:
        if isinstance(value, float):
            return not math.isnan(value)
        if isinstance(value, dict):
            return all(_no_nan(v) for v in value.values())
        if isinstance(value, list):
            return all(_no_nan(v) for v in value)
        return True

    assert _no_nan(snapshot)
