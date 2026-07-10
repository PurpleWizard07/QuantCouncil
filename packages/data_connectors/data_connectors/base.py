"""Abstract OHLCV connector contract.

Every market data source used by QuantCouncil implements this interface, so
the rest of the system depends on exactly one DataFrame shape.

Downstream code (quant_engine, the cache, the API) should call
``get_ohlcv`` -- not ``fetch_daily`` directly. ``fetch_daily`` is the thin,
provider-specific piece each connector implements; ``get_ohlcv`` is the
stable public entry point that validates inputs, enforces the v1
daily-only scope, and runs the raw response through
``data_connectors.validation.validate_ohlcv`` before handing it back. This
split is what makes connectors swappable: any code holding an
``OHLCVConnector`` (yfinance today, OpenBB later) can call the same method
and get the same guaranteed shape back.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import date, datetime

import pandas as pd

from data_connectors.validation import validate_ohlcv

DAILY_TIMEFRAME = "1d"
"""The only timeframe QuantCouncil v1 supports."""


class OHLCVConnector(ABC):
    """Abstract base class for daily OHLCV data sources.

    DataFrame contract (enforced by ``get_ohlcv`` via
    ``data_connectors.validation``):
        - Columns exactly ``[date, open, high, low, close, volume]``.
        - Rows sorted by ascending ``date``.
        - ``date`` values are tz-naive (dates or tz-naive timestamps).
        - No duplicate dates.
        - No NaN rows -- rows with any missing OHLCV value are dropped or the
          fetch fails, never silently passed through.

    Connectors that cannot meet the contract must raise rather than return
    malformed data; quant_engine assumes this contract holds.
    """

    @abstractmethod
    def fetch_daily(self, symbol: str, start: date, end: date) -> pd.DataFrame:
        """Fetch daily OHLCV bars for one symbol over [start, end] inclusive.

        Provider-specific: implemented by each connector subclass. Callers
        outside this package should prefer ``get_ohlcv``, which wraps this
        method with input validation and contract validation.

        Args:
            symbol: Plain NSE symbol from the universe (e.g. "RELIANCE"),
                without any exchange suffix; each connector maps it to its
                own provider format.
            start: First calendar date of the range (inclusive).
            end: Last calendar date of the range (inclusive).

        Returns:
            DataFrame satisfying the contract documented on this class.
        """
        ...

    def get_ohlcv(
        self,
        symbol: str,
        start_date: date | str,
        end_date: date | str,
        timeframe: str = "1d",
    ) -> pd.DataFrame:
        """Fetch and validate daily OHLCV bars. The public entry point.

        This is what downstream code should call -- never ``fetch_daily``
        directly. It validates inputs, rejects anything other than daily
        bars (v1 scope), delegates to ``fetch_daily`` for the provider call,
        and normalizes/validates the result via
        ``data_connectors.validation.validate_ohlcv`` before returning.

        Args:
            symbol: Plain NSE symbol (e.g. "RELIANCE", "M&M").
            start_date: Range start (inclusive). A ``datetime.date`` or an
                ISO ``"YYYY-MM-DD"`` string.
            end_date: Range end (inclusive). Same accepted types as
                ``start_date``.
            timeframe: Must be ``"1d"`` -- daily bars only in v1. Any other
                value raises ``ValueError``.

        Returns:
            DataFrame satisfying the ``OHLCVConnector`` contract.

        Raises:
            ValueError: If ``timeframe`` isn't ``"1d"``, if either date
                cannot be parsed, or if ``start_date`` is after ``end_date``.
            DataFetchError: If the underlying provider fetch fails (raised
                by the concrete connector's ``fetch_daily``).
            DataValidationError: If the fetched data violates the OHLCV
                contract.
        """
        start, end = _validate_get_ohlcv_args(start_date, end_date, timeframe)
        raw = self.fetch_daily(symbol, start, end)
        return validate_ohlcv(raw)


def _coerce_date(value: date | str, field_name: str) -> date:
    """Coerce a ``datetime.date``/``datetime.datetime``/ISO string to a date.

    Args:
        value: The value to coerce.
        field_name: Used only to produce a helpful error message.

    Raises:
        ValueError: If ``value`` is not a date/datetime and not a
            ``"YYYY-MM-DD"`` string.
    """
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    if isinstance(value, str):
        try:
            return datetime.strptime(value, "%Y-%m-%d").date()
        except ValueError as exc:
            raise ValueError(
                f"{field_name}={value!r} is not a valid ISO date string "
                "(expected 'YYYY-MM-DD')."
            ) from exc
    raise ValueError(
        f"{field_name} must be a datetime.date (or datetime.datetime) or an "
        f"ISO 'YYYY-MM-DD' string, got {type(value).__name__}."
    )


def _validate_get_ohlcv_args(
    start_date: date | str, end_date: date | str, timeframe: str
) -> tuple[date, date]:
    """Shared ``get_ohlcv`` input validation, reused by ``CachedConnector``.

    Raises:
        ValueError: If ``timeframe`` isn't ``"1d"``, either date is
            unparseable, or ``start_date`` is after ``end_date``.
    """
    if timeframe != DAILY_TIMEFRAME:
        raise ValueError(
            f"Unsupported timeframe {timeframe!r}: QuantCouncil v1 supports "
            f"daily bars only ({DAILY_TIMEFRAME!r}). Intraday/weekly/monthly "
            "timeframes are out of scope."
        )
    start = _coerce_date(start_date, "start_date")
    end = _coerce_date(end_date, "end_date")
    if start > end:
        raise ValueError(
            f"start_date ({start.isoformat()}) must be on or before "
            f"end_date ({end.isoformat()})."
        )
    return start, end
