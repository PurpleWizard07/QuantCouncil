"""yfinance-backed fundamentals connector (raw fetch only).

Fetches company profile fields (from yfinance's ``.info``) and the last five
annual financial statements (income statement, balance sheet, cash flow) for
one NSE symbol. Free data only, via the same ``yfinance`` package the OHLCV
connector already depends on -- no new dependency, no paid data source (see
non-goals.md: QuantCouncil never depends on paid data).

This module deliberately mirrors ``yfinance_connector.py``'s shape (a class
wrapping ``yfinance``, symbol mapped via ``to_yfinance_symbol``, provider
failures wrapped in ``DataFetchError``) but does not implement the
``OHLCVConnector`` contract: fundamentals are not a ``[date, OHLCV]`` bar
series, so a smaller, separate interface fits better than forcing the OHLCV
shape onto it.

Ratio computation (ROE, current ratio, ...) is NOT done here -- this module
only fetches and lightly normalizes yfinance's raw response. Deterministic
ratio math lives in ``quant_engine.fundamentals``, matching the project's
rule that quant_engine is the sole source of truth for computed numbers.

Not yet cached (unlike OHLCV): every call re-fetches from yfinance. Company
fundamentals change at most quarterly, so this is a reasonable v1
simplification, not an oversight -- add a cache here (mirroring
``data_connectors.cache``) if request volume ever warrants it.

One observed quirk worth knowing when reading a response: yfinance's
``.info`` is assembled from several upstream Yahoo modules, and under rate
limiting it can come back partially populated -- a field present on one call
can be absent on the next for the same symbol (seen with
``priceToSalesTrailing12Months`` on RELIANCE). So a null field means "not in
this response", which is usually but not always "the company doesn't report
it". Re-request before concluding a field is permanently unavailable.
"""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from data_connectors.exceptions import DataFetchError
from data_connectors.universe import to_yfinance_symbol

try:
    import yfinance as yf
except ImportError as exc:  # pragma: no cover - exercised only without yfinance installed
    raise ImportError(
        "The 'yfinance' package is required for YFinanceFundamentalsConnector "
        "but is not installed. Install it with:\n"
        "    .venv/Scripts/pip.exe install yfinance\n"
        "or refresh all data_connectors dependencies with:\n"
        "    .venv/Scripts/pip.exe install -e packages/data_connectors"
    ) from exc


@dataclass
class RawFundamentals:
    """Unprocessed fundamentals data for one symbol, straight from yfinance.

    Attributes:
        symbol: Plain NSE symbol (e.g. "RELIANCE"), not the yfinance-suffixed
            form.
        info: yfinance's company/quote-summary snapshot dict (P/E, margins,
            EPS, dividends, ...). Which fields are present varies by
            company; missing keys are normal, not an error.
        income_stmt: Annual income statement -- one row per line item, one
            column per fiscal year-end (most recent first), up to five
            years. Empty DataFrame if yfinance has none.
        balance_sheet: Annual balance sheet, same column/index shape as
            ``income_stmt``. Financials (e.g. banks) omit the
            current/non-current split entirely -- that is a correct
            absence, not missing data.
        cashflow: Annual cash flow statement, same column/index shape.
    """

    symbol: str
    info: dict
    income_stmt: pd.DataFrame
    balance_sheet: pd.DataFrame
    cashflow: pd.DataFrame


class YFinanceFundamentalsConnector:
    """Fetches raw company fundamentals from Yahoo Finance (free data)."""

    def fetch_fundamentals(self, symbol: str) -> RawFundamentals:
        """Fetch ``.info`` plus up to five annual statements for ``symbol``.

        Args:
            symbol: Plain NSE symbol from the universe (e.g. "RELIANCE").

        Returns:
            A ``RawFundamentals`` bundle. Missing individual ``.info``
            fields or missing/short statement history are normal (not every
            company reports every field) and show up as absent keys / fewer
            columns, not as an error.

        Raises:
            DataFetchError: If ``yfinance`` raises, or the ``.info``
                response comes back essentially empty (no company name at
                all) -- the same signal the OHLCV connector treats as an
                invalid symbol, delisting, or provider outage.
        """
        yf_symbol = to_yfinance_symbol(symbol)
        ticker = yf.Ticker(yf_symbol)

        try:
            info = ticker.info
            income_stmt = ticker.income_stmt
            balance_sheet = ticker.balance_sheet
            cashflow = ticker.cashflow
        except Exception as exc:  # yfinance can raise a variety of exception types
            raise DataFetchError(
                f"yfinance raised while fetching fundamentals for {symbol!r} "
                f"({yf_symbol}): {exc}"
            ) from exc

        if not info.get("longName") and not info.get("shortName"):
            raise DataFetchError(
                f"yfinance returned no usable fundamentals for {symbol!r} "
                f"({yf_symbol}) -- no company name in the response. Possible "
                "causes: invalid/mistyped symbol, the stock was delisted, or "
                "a network/Yahoo Finance outage."
            )

        return RawFundamentals(
            symbol=symbol,
            info=info,
            income_stmt=income_stmt if income_stmt is not None else pd.DataFrame(),
            balance_sheet=balance_sheet if balance_sheet is not None else pd.DataFrame(),
            cashflow=cashflow if cashflow is not None else pd.DataFrame(),
        )
