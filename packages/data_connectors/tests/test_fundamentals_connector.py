"""Tests for YFinanceFundamentalsConnector.fetch_fundamentals with yfinance
fully mocked.

No network access: every test monkeypatches
``data_connectors.fundamentals.yf.Ticker`` with a fake constructor returning
a controlled, in-memory ``info`` dict and statement DataFrames shaped like
real yfinance responses (index=line items, columns=period end dates).
"""

from __future__ import annotations

import pandas as pd
import pytest

import data_connectors.fundamentals as fnd
from data_connectors.exceptions import DataFetchError


def _statement_frame(periods: list[str], rows: dict[str, list[float]]) -> pd.DataFrame:
    """Build a frame shaped like yfinance's statement output.

    ``rows`` maps line-item label -> one value per period, in the same
    (most-recent-first) order as ``periods``.
    """
    columns = pd.to_datetime(periods)
    return pd.DataFrame(list(rows.values()), index=list(rows.keys()), columns=columns)


class _FakeTicker:
    def __init__(self, info, income_stmt=None, balance_sheet=None, cashflow=None):
        self._info = info
        self._income_stmt = income_stmt if income_stmt is not None else pd.DataFrame()
        self._balance_sheet = balance_sheet if balance_sheet is not None else pd.DataFrame()
        self._cashflow = cashflow if cashflow is not None else pd.DataFrame()

    @property
    def info(self):
        return self._info

    @property
    def income_stmt(self):
        return self._income_stmt

    @property
    def balance_sheet(self):
        return self._balance_sheet

    @property
    def cashflow(self):
        return self._cashflow


class _RaisingTicker:
    """A fake Ticker whose `.info` property raises, simulating a network failure."""

    @property
    def info(self):
        raise RuntimeError("simulated network failure")


_INFO = {"longName": "Reliance Industries Limited", "trailingPE": 23.9}
_INCOME_STMT = _statement_frame(
    ["2025-03-31", "2024-03-31"], {"Total Revenue": [900_000.0, 800_000.0], "Net Income": [70_000.0, 60_000.0]}
)
_BALANCE_SHEET = _statement_frame(
    ["2025-03-31", "2024-03-31"],
    {"Total Assets": [1_500_000.0, 1_400_000.0], "Stockholders Equity": [900_000.0, 850_000.0]},
)
_CASHFLOW = _statement_frame(["2025-03-31", "2024-03-31"], {"Operating Cash Flow": [120_000.0, 110_000.0]})


def test_fetch_fundamentals_happy_path(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        fnd.yf,
        "Ticker",
        lambda symbol: _FakeTicker(_INFO, _INCOME_STMT, _BALANCE_SHEET, _CASHFLOW),
    )

    connector = fnd.YFinanceFundamentalsConnector()
    out = connector.fetch_fundamentals("RELIANCE")

    assert isinstance(out, fnd.RawFundamentals)
    assert out.symbol == "RELIANCE"
    assert out.info == _INFO
    assert out.income_stmt.equals(_INCOME_STMT)
    assert out.balance_sheet.equals(_BALANCE_SHEET)
    assert out.cashflow.equals(_CASHFLOW)


def test_fetch_fundamentals_uses_yfinance_symbol_mapping(monkeypatch: pytest.MonkeyPatch) -> None:
    captured = {}

    def fake_ticker(symbol):
        captured["symbol"] = symbol
        return _FakeTicker(_INFO)

    monkeypatch.setattr(fnd.yf, "Ticker", fake_ticker)

    connector = fnd.YFinanceFundamentalsConnector()
    connector.fetch_fundamentals("M&M")

    assert captured["symbol"] == "M&M.NS"


def test_fetch_fundamentals_shortname_only_is_accepted(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(fnd.yf, "Ticker", lambda symbol: _FakeTicker({"shortName": "Reliance"}))

    connector = fnd.YFinanceFundamentalsConnector()
    out = connector.fetch_fundamentals("RELIANCE")

    assert out.info == {"shortName": "Reliance"}


def test_fetch_fundamentals_empty_info_raises_data_fetch_error(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(fnd.yf, "Ticker", lambda symbol: _FakeTicker({"trailingPegRatio": None}))

    connector = fnd.YFinanceFundamentalsConnector()
    with pytest.raises(DataFetchError, match="no usable fundamentals"):
        connector.fetch_fundamentals("NOTAREALSYMBOL")


def test_fetch_fundamentals_ticker_raising_exception_becomes_data_fetch_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(fnd.yf, "Ticker", lambda symbol: _RaisingTicker())

    connector = fnd.YFinanceFundamentalsConnector()
    with pytest.raises(DataFetchError, match="simulated network failure"):
        connector.fetch_fundamentals("RELIANCE")


def test_fetch_fundamentals_none_statements_default_to_empty_dataframe(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        fnd.yf,
        "Ticker",
        lambda symbol: _FakeTicker(_INFO, income_stmt=None, balance_sheet=None, cashflow=None),
    )

    connector = fnd.YFinanceFundamentalsConnector()
    out = connector.fetch_fundamentals("RELIANCE")

    assert out.income_stmt.empty
    assert out.balance_sheet.empty
    assert out.cashflow.empty
