"""Fundamental-analysis ratios and statement history.

Pure, deterministic functions over the raw ``.info`` dict and annual
financial statement DataFrames fetched by
``data_connectors.fundamentals.YFinanceFundamentalsConnector``. Mirrors
``quant_engine.indicators``: no network access, no side effects, every
number traceable to a specific input field.

Unit conventions (verified empirically against yfinance's raw balance-sheet
figures for RELIANCE/INFY/ITC -- yfinance is inconsistent about this across
fields, so this is documented rather than assumed):
    - ``profit_margin``, ``operating_margin``, ``return_on_assets``,
      ``return_on_equity``, ``revenue_growth``, ``earnings_growth``,
      ``payout_ratio`` are fractions (``0.066`` means 6.6%).
    - ``dividend_yield_pct`` and ``debt_to_equity_pct`` are already
      percentage points (``36.65`` means a debt/equity ratio of ~0.37, not
      36.65x) -- confirmed by cross-checking against ``Total Debt`` /
      ``Stockholders Equity`` on the raw balance sheet.
    - ``current_ratio`` / ``quick_ratio`` are always computed here (yfinance
      never populates them for NSE names) and are plain ratios (``1.86``
      means 1.86x).

Current ratio / quick ratio are None for banks and similar financials, which
do not report a classified (current vs. non-current) balance sheet -- that
is a correct absence, not a bug.

Two ratios yfinance's ``.info`` sometimes omits (return on assets, return on
equity) are populated for some companies but not others -- an inconsistency
in Yahoo's own data, not a sector pattern. This module trusts ``.info`` when
present (a TTM-based figure, likely more precise) and falls back to
computing an annual approximation from the statements only when ``.info``
omits it.
"""

from __future__ import annotations

import math
from typing import Any

import pandas as pd

_HISTORY_FIELDS = (
    ("total_revenue", "Total Revenue", "income_stmt"),
    ("net_income", "Net Income", "income_stmt"),
    ("total_assets", "Total Assets", "balance_sheet"),
    ("total_liabilities", "Total Liabilities Net Minority Interest", "balance_sheet"),
    ("stockholders_equity", "Stockholders Equity", "balance_sheet"),
    ("operating_cash_flow", "Operating Cash Flow", "cashflow"),
    ("free_cash_flow", "Free Cash Flow", "cashflow"),
)
DEFAULT_HISTORY_LIMIT = 5


def _clean(value: Any) -> float | None:
    """Coerce a raw info/statement scalar to a JSON-safe float, or None.

    Handles yfinance's mix of Python floats, numpy scalars, ``None``, and
    (for unreported line items) ``NaN`` -- JSON has no NaN, so it always
    becomes ``None`` here rather than leaking through to the API response.
    """
    if value is None:
        return None
    try:
        result = float(value)
    except (TypeError, ValueError):
        return None
    return None if math.isnan(result) else result


def _latest(df: pd.DataFrame, label: str) -> float | None:
    """Most recent period's value for ``label``, or None if unavailable.

    ``df`` is a statement DataFrame shaped like yfinance's output: one row
    per line item, one column per period, most recent period first. Returns
    None if ``label`` isn't a row (the company doesn't report that line item
    -- e.g. banks have no "Current Assets" row) or the frame has no columns.
    """
    if df.empty or df.shape[1] == 0 or label not in df.index:
        return None
    return _clean(df.loc[label].iloc[0])


def return_on_equity(
    info: dict, income_stmt: pd.DataFrame, balance_sheet: pd.DataFrame
) -> float | None:
    """ROE: ``.info``'s value if present, else ``Net Income / Stockholders Equity``."""
    from_info = _clean(info.get("returnOnEquity"))
    if from_info is not None:
        return from_info
    net_income = _latest(income_stmt, "Net Income")
    equity = _latest(balance_sheet, "Stockholders Equity")
    if net_income is None or not equity:
        return None
    return net_income / equity


def return_on_assets(
    info: dict, income_stmt: pd.DataFrame, balance_sheet: pd.DataFrame
) -> float | None:
    """ROA: ``.info``'s value if present, else ``Net Income / Total Assets``."""
    from_info = _clean(info.get("returnOnAssets"))
    if from_info is not None:
        return from_info
    net_income = _latest(income_stmt, "Net Income")
    assets = _latest(balance_sheet, "Total Assets")
    if net_income is None or not assets:
        return None
    return net_income / assets


def current_ratio(balance_sheet: pd.DataFrame) -> float | None:
    """``Current Assets / Current Liabilities``.

    None for companies without a classified balance sheet (e.g. banks) --
    yfinance simply has no "Current Assets" row for them, which is correct:
    the current/non-current split isn't a meaningful concept for a bank's
    balance sheet.
    """
    assets = _latest(balance_sheet, "Current Assets")
    liabilities = _latest(balance_sheet, "Current Liabilities")
    if assets is None or not liabilities:
        return None
    return assets / liabilities


def quick_ratio(balance_sheet: pd.DataFrame) -> float | None:
    """``(Current Assets - Inventory) / Current Liabilities``.

    A company with no "Inventory" row (e.g. an IT services company) is
    treated as having zero inventory, not as missing data -- so quick ratio
    correctly equals current ratio for inventory-free businesses.
    """
    assets = _latest(balance_sheet, "Current Assets")
    liabilities = _latest(balance_sheet, "Current Liabilities")
    if assets is None or not liabilities:
        return None
    inventory = _latest(balance_sheet, "Inventory") or 0.0
    return (assets - inventory) / liabilities


def annual_history(
    income_stmt: pd.DataFrame,
    balance_sheet: pd.DataFrame,
    cashflow: pd.DataFrame,
    limit: int = DEFAULT_HISTORY_LIMIT,
) -> list[dict[str, Any]]:
    """Curated year-by-year statement history, newest fiscal year first.

    Driven by ``income_stmt``'s columns (revenue/net income are the most
    consistently reported line items). The three annual statements can have
    different period counts for the same company (observed on HDFCBANK: 5
    income-statement years but 4 balance-sheet years), so a period missing
    from ``balance_sheet`` or ``cashflow`` yields None for that period's
    fields from the missing statement, not a dropped row.

    Args:
        limit: Maximum number of most-recent fiscal years to include.

    Returns:
        Rows newest-first, each with ``fiscal_year_end`` (ISO date) plus the
        fields in ``_HISTORY_FIELDS`` (total_revenue, net_income,
        total_assets, total_liabilities, stockholders_equity,
        operating_cash_flow, free_cash_flow). Empty list if ``income_stmt``
        has no columns.
    """
    if income_stmt.empty:
        return []

    statements = {
        "income_stmt": income_stmt,
        "balance_sheet": balance_sheet,
        "cashflow": cashflow,
    }
    rows: list[dict[str, Any]] = []
    for period in income_stmt.columns[:limit]:
        row: dict[str, Any] = {"fiscal_year_end": pd.Timestamp(period).date().isoformat()}
        for out_key, label, statement_name in _HISTORY_FIELDS:
            df = statements[statement_name]
            row[out_key] = (
                _clean(df.loc[label, period])
                if (not df.empty and period in df.columns and label in df.index)
                else None
            )
        rows.append(row)
    return rows


def _fiscal_date(epoch_seconds: Any) -> str | None:
    """Convert one of yfinance's Unix-epoch ``.info`` fields to an ISO date."""
    if epoch_seconds is None:
        return None
    try:
        return pd.Timestamp(epoch_seconds, unit="s").date().isoformat()
    except (TypeError, ValueError, OverflowError):
        return None


def build_snapshot(
    info: dict,
    income_stmt: pd.DataFrame,
    balance_sheet: pd.DataFrame,
    cashflow: pd.DataFrame,
    history_limit: int = DEFAULT_HISTORY_LIMIT,
) -> dict[str, Any]:
    """Assemble the fundamentals snapshot served by ``/assets/{symbol}/fundamentals``.

    Combines ``.info`` passthrough fields with the ratios this module
    computes (see the module docstring for the ``.info``-vs-computed
    fallback rule and unit conventions) and the curated annual statement
    history. Every leaf value is a plain float, string, or None -- never
    NaN, which is invalid JSON.

    Returns:
        A nested dict: ``profile``, ``valuation``, ``per_share``,
        ``dividends``, ``profitability``, ``growth``, ``financial_health``,
        ``annual_history``, and ``as_of`` (the fiscal year-end / quarter
        ``.info`` itself reports).
    """
    return {
        "profile": {
            "name": info.get("longName") or info.get("shortName"),
            "sector": info.get("sector"),
            "industry": info.get("industry"),
            "currency": info.get("currency"),
        },
        "valuation": {
            "market_cap": _clean(info.get("marketCap")),
            "trailing_pe": _clean(info.get("trailingPE")),
            "forward_pe": _clean(info.get("forwardPE")),
            "price_to_book": _clean(info.get("priceToBook")),
            "price_to_sales_ttm": _clean(info.get("priceToSalesTrailing12Months")),
            "ev_to_ebitda": _clean(info.get("enterpriseToEbitda")),
        },
        "per_share": {
            "trailing_eps": _clean(info.get("trailingEps")),
            "forward_eps": _clean(info.get("forwardEps")),
            "book_value_per_share": _clean(info.get("bookValue")),
        },
        "dividends": {
            "dividend_rate": _clean(info.get("dividendRate")),
            "dividend_yield_pct": _clean(info.get("dividendYield")),
            "payout_ratio": _clean(info.get("payoutRatio")),
        },
        "profitability": {
            "profit_margin": _clean(info.get("profitMargins")),
            "operating_margin": _clean(info.get("operatingMargins")),
            "return_on_assets": return_on_assets(info, income_stmt, balance_sheet),
            "return_on_equity": return_on_equity(info, income_stmt, balance_sheet),
        },
        "growth": {
            "revenue_growth": _clean(info.get("revenueGrowth")),
            "earnings_growth": _clean(info.get("earningsGrowth")),
        },
        "financial_health": {
            "debt_to_equity_pct": _clean(info.get("debtToEquity")),
            "current_ratio": current_ratio(balance_sheet),
            "quick_ratio": quick_ratio(balance_sheet),
            "total_cash": _clean(info.get("totalCash")),
            "total_debt": _clean(info.get("totalDebt")),
        },
        "annual_history": annual_history(income_stmt, balance_sheet, cashflow, limit=history_limit),
        "as_of": {
            "last_fiscal_year_end": _fiscal_date(info.get("lastFiscalYearEnd")),
            "most_recent_quarter": _fiscal_date(info.get("mostRecentQuarter")),
        },
    }
