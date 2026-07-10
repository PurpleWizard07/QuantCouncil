"""yfinance-backed OHLCV connector (Phase 2).

Uses the free Yahoo Finance data source via the ``yfinance`` package -- no
paid data anywhere in QuantCouncil v1. NSE symbols are mapped to Yahoo
tickers with the ".NS" suffix (e.g. "RELIANCE" -> "RELIANCE.NS"). Daily bars
only, matching the project's daily-timeframe scope.

Adjusted vs. unadjusted prices (v1 simplification): this connector calls
``yfinance`` with ``auto_adjust=False`` and keeps the raw OHLC as reported,
deliberately not correcting for splits/bonuses. Practically this means a
stock split or bonus issue shows up as a sharp price jump on the ex-date
rather than a smooth adjustment. This is documented, not accidental: v1
prioritizes simplicity over a fully split/dividend-adjusted price series.
``validate_ohlcv_report`` (see ``data_connectors.validation``) can flag these
jumps as "possible corporate action" warnings for anyone who wants to notice
them.
"""

from __future__ import annotations

from datetime import date, timedelta

import pandas as pd

from data_connectors.base import OHLCVConnector
from data_connectors.exceptions import DataFetchError
from data_connectors.universe import to_yfinance_symbol

try:
    import yfinance as yf
except ImportError as exc:  # pragma: no cover - exercised only without yfinance installed
    raise ImportError(
        "The 'yfinance' package is required for YFinanceConnector but is "
        "not installed. Install it with:\n"
        "    .venv/Scripts/pip.exe install yfinance\n"
        "or refresh all data_connectors dependencies with:\n"
        "    .venv/Scripts/pip.exe install -e packages/data_connectors"
    ) from exc

_OHLCV_COLUMNS = ["open", "high", "low", "close", "volume"]


class YFinanceConnector(OHLCVConnector):
    """Daily OHLCV connector backed by Yahoo Finance (free data)."""

    def fetch_daily(self, symbol: str, start: date, end: date) -> pd.DataFrame:
        """Fetch daily bars for ``symbol`` from Yahoo Finance.

        The plain NSE symbol is converted with
        :func:`data_connectors.universe.to_yfinance_symbol` (".NS" suffix)
        before querying. The returned DataFrame satisfies the
        ``OHLCVConnector`` contract (columns ``[date, open, high, low,
        close, volume]``, ascending tz-naive dates, no duplicates, no NaN
        rows) directly -- this method does its own cleaning rather than
        relying solely on the shared validation layer, since it knows the
        specific shapes ``yfinance`` can return.

        Args:
            symbol: Plain NSE symbol (e.g. "RELIANCE").
            start: Range start (inclusive).
            end: Range end (inclusive).

        Returns:
            Cleaned OHLCV DataFrame for ``[start, end]``.

        Raises:
            DataFetchError: If ``yfinance`` raises, or returns an empty/
                malformed response (invalid symbol, delisted, no data in
                range, or a network/Yahoo Finance outage).
        """
        yf_symbol = to_yfinance_symbol(symbol)
        # yfinance treats `end` as exclusive; add one day so the requested
        # end date is included, matching the OHLCVConnector contract.
        exclusive_end = end + timedelta(days=1)

        try:
            raw = yf.download(
                yf_symbol,
                start=start,
                end=exclusive_end,
                auto_adjust=False,
                progress=False,
            )
        except Exception as exc:  # yfinance can raise a variety of exception types
            raise DataFetchError(
                f"yfinance raised while fetching {symbol!r} ({yf_symbol}) "
                f"for [{start}, {end}]: {exc}"
            ) from exc

        if raw is None or raw.empty:
            raise DataFetchError(
                f"yfinance returned no data for {symbol!r} ({yf_symbol}) "
                f"over [{start}, {end}]. Possible causes: invalid/mistyped "
                "symbol, the stock was delisted or not yet listed in this "
                "range, no trading days fall in this range, or a network/"
                "Yahoo Finance outage."
            )

        return _clean_yfinance_frame(raw, symbol=symbol, yf_symbol=yf_symbol)


def _clean_yfinance_frame(raw: pd.DataFrame, *, symbol: str, yf_symbol: str) -> pd.DataFrame:
    """Normalize a raw ``yf.download`` frame into the OHLCVConnector contract."""
    df = raw.copy()

    if isinstance(df.columns, pd.MultiIndex):
        # yf.download returns MultiIndex (Price, Ticker) columns even for a
        # single ticker in recent yfinance versions; there is exactly one
        # ticker here, so the top level ("Price") uniquely identifies each
        # field and can be flattened safely.
        df.columns = df.columns.get_level_values(0)

    df = df.reset_index()
    df.columns = [str(c).lower() for c in df.columns]
    df = df.rename(columns={"adj close": "adj_close"})

    missing = [c for c in ["date", *_OHLCV_COLUMNS] if c not in df.columns]
    if missing:
        raise DataFetchError(
            f"yfinance response for {symbol!r} ({yf_symbol}) is missing "
            f"expected column(s) {missing}; got {list(df.columns)}."
        )
    df = df[["date", *_OHLCV_COLUMNS]]

    dates = pd.to_datetime(df["date"])
    if dates.dt.tz is not None:
        dates = dates.dt.tz_localize(None)
    df["date"] = dates

    df = df.drop_duplicates(subset="date", keep="first")
    df = df.dropna(subset=["date", *_OHLCV_COLUMNS], how="any")
    df = df.sort_values("date").reset_index(drop=True)
    return df
