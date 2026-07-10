"""Validation of the OHLCV DataFrame contract shared by all connectors.

Every connector's public ``get_ohlcv`` (see ``data_connectors.base``) routes
its raw provider response through :func:`validate_ohlcv` before returning it,
so the rest of the system (quant_engine, the API, the cache) can rely on one
guaranteed DataFrame shape:

    - Columns exactly ``[date, open, high, low, close, volume]``.
    - ``date`` parseable, tz-naive, no duplicates.
    - OHLC and volume numeric; volume >= 0.
    - ``high`` is the row max and ``low`` is the row min (within a tiny
      relative tolerance for floating point noise).
    - Rows sorted ascending by date.
    - No NaN rows (dropped, with the count logged).

Fatal contract violations (bad columns, duplicate dates, high < low, negative
volume, out-of-tolerance high/low bounds, not enough rows) raise
:class:`DataValidationError`. :func:`validate_ohlcv_report` additionally
returns a list of *non-fatal* warning strings (e.g. large single-day moves
that look like an unadjusted corporate action) for callers that want to
surface them without failing the fetch.
"""

from __future__ import annotations

import logging

import pandas as pd

logger = logging.getLogger(__name__)

REQUIRED_COLUMNS: list[str] = ["date", "open", "high", "low", "close", "volume"]
"""The OHLCVConnector contract's exact column set, in canonical order."""

_NUMERIC_COLUMNS: list[str] = ["open", "high", "low", "close", "volume"]
_TOLERANCE = 1e-6
_CORPORATE_ACTION_THRESHOLD = 0.40


class DataValidationError(ValueError):
    """Raised when an OHLCV DataFrame violates the shared contract."""


def validate_ohlcv(df: pd.DataFrame, min_rows: int | None = None) -> pd.DataFrame:
    """Validate and normalize an OHLCV DataFrame against the shared contract.

    Args:
        df: Candidate OHLCV frame. Must contain at least the columns
            ``[date, open, high, low, close, volume]``; extra columns are
            dropped from the result.
        min_rows: If given, raise if fewer than this many rows remain after
            cleaning (e.g. enforcing a minimum lookback window).

    Returns:
        A new DataFrame with exactly ``REQUIRED_COLUMNS``, tz-naive
        datetime64 ``date``, sorted ascending, no duplicate dates, no NaN
        rows.

    Raises:
        DataValidationError: On any fatal contract violation -- see the
            module docstring for the full list of checks.
    """
    clean, nan_dropped = _clean_and_validate(df, min_rows)
    if nan_dropped:
        logger.warning(
            "validate_ohlcv: dropped %d row(s) with missing OHLCV value(s)",
            nan_dropped,
        )
    return clean


def validate_ohlcv_report(
    df: pd.DataFrame, min_rows: int | None = None
) -> tuple[pd.DataFrame, list[str]]:
    """Like :func:`validate_ohlcv`, plus a list of non-fatal warnings.

    In addition to everything :func:`validate_ohlcv` checks, this flags
    single-day close-to-close moves larger than 40% as possible (unadjusted)
    corporate actions -- e.g. a stock split, bonus issue, or large dividend
    that this v1 unadjusted-price pipeline does not correct for (see
    ``YFinanceConnector``'s ``auto_adjust=False`` choice). These are
    warnings, not errors: a genuine 40%+ move can also be legitimate news.

    Args:
        df: Candidate OHLCV frame, same requirements as :func:`validate_ohlcv`.
        min_rows: Same as :func:`validate_ohlcv`.

    Returns:
        Tuple of ``(clean_df, warnings)`` where ``warnings`` is a list of
        human-readable strings (empty if nothing looked off).

    Raises:
        DataValidationError: Same fatal conditions as :func:`validate_ohlcv`.
    """
    clean, nan_dropped = _clean_and_validate(df, min_rows)
    warnings: list[str] = []
    if nan_dropped:
        warnings.append(f"Dropped {nan_dropped} row(s) with missing OHLCV value(s).")
    warnings.extend(_corporate_action_warnings(clean))
    return clean, warnings


def _clean_and_validate(
    df: pd.DataFrame, min_rows: int | None
) -> tuple[pd.DataFrame, int]:
    """Shared implementation behind both public entry points.

    Returns:
        Tuple of ``(clean_df, nan_rows_dropped_count)``.
    """
    _check_required_columns(df)
    df = df.copy()
    df["date"] = _parse_dates(df)
    _check_no_duplicate_dates(df)
    df, nan_dropped = _coerce_numeric_and_drop_nan(df)

    if (df["volume"] < 0).any():
        n_bad = int((df["volume"] < 0).sum())
        raise DataValidationError(
            f"OHLCV frame has {n_bad} row(s) with negative volume; "
            "volume must be >= 0."
        )

    if (df["high"] < df["low"]).any():
        n_bad = int((df["high"] < df["low"]).sum())
        raise DataValidationError(
            f"OHLCV frame has {n_bad} row(s) where high < low."
        )

    violation = (
        _exceeds(df["open"], df["high"], _TOLERANCE)
        | _exceeds(df["close"], df["high"], _TOLERANCE)
        | _exceeds(df["low"], df["open"], _TOLERANCE)
        | _exceeds(df["low"], df["close"], _TOLERANCE)
    )
    if violation.any():
        raise DataValidationError(
            f"OHLCV frame has {int(violation.sum())} row(s) violating "
            "high/low bounds (high must be >= open, close, and low; low "
            f"must be <= open, close, and high), beyond a relative "
            f"tolerance of {_TOLERANCE:g}."
        )

    df = df.sort_values("date").reset_index(drop=True)

    if min_rows is not None and len(df) < min_rows:
        raise DataValidationError(
            f"Not enough rows for requested lookback: got {len(df)}, "
            f"need at least {min_rows}."
        )

    return df[REQUIRED_COLUMNS].reset_index(drop=True), nan_dropped


def _check_required_columns(df: pd.DataFrame) -> None:
    missing = [c for c in REQUIRED_COLUMNS if c not in df.columns]
    if missing:
        raise DataValidationError(
            f"OHLCV frame is missing required column(s) {missing}; "
            f"got columns {list(df.columns)}."
        )


def _parse_dates(df: pd.DataFrame) -> pd.Series:
    """Coerce the ``date`` column to tz-naive datetime64, erroring on failure."""
    parsed = pd.to_datetime(df["date"], errors="coerce")
    if parsed.dt.tz is not None:
        parsed = parsed.dt.tz_localize(None)
    if parsed.isna().any():
        n_bad = int(parsed.isna().sum())
        raise DataValidationError(
            f"OHLCV frame has {n_bad} row(s) with a missing or unparseable "
            "'date' value."
        )
    return parsed


def _check_no_duplicate_dates(df: pd.DataFrame) -> None:
    dup_mask = df["date"].duplicated(keep=False)
    if dup_mask.any():
        examples = sorted(
            {_as_date_str(d) for d in df.loc[dup_mask, "date"]}
        )[:5]
        raise DataValidationError(
            f"OHLCV frame has {int(dup_mask.sum())} row(s) with duplicate "
            f"dates (e.g. {examples}); each date must appear at most once."
        )


def _coerce_numeric_and_drop_nan(df: pd.DataFrame) -> tuple[pd.DataFrame, int]:
    """Coerce OHLCV columns to numeric and drop rows with any resulting NaN."""
    for col in _NUMERIC_COLUMNS:
        df[col] = pd.to_numeric(df[col], errors="coerce")
    nan_mask = df[_NUMERIC_COLUMNS].isna().any(axis=1)
    nan_dropped = int(nan_mask.sum())
    if nan_dropped:
        df = df.loc[~nan_mask].reset_index(drop=True)
    return df, nan_dropped


def _exceeds(lhs: pd.Series, rhs: pd.Series, tol: float) -> pd.Series:
    """True where ``lhs`` should not exceed ``rhs`` but does, past ``tol``.

    Uses a relative tolerance scaled to the larger of the two magnitudes
    (floored at 1.0) so it behaves sensibly for both penny stocks and
    large-cap prices in the thousands.
    """
    scale = pd.concat([lhs.abs(), rhs.abs()], axis=1).max(axis=1).clip(lower=1.0)
    return (lhs - rhs) > tol * scale


def _corporate_action_warnings(
    df: pd.DataFrame, threshold: float = _CORPORATE_ACTION_THRESHOLD
) -> list[str]:
    """Flag single-day close-to-close moves larger than ``threshold`` (40%)."""
    if len(df) < 2:
        return []
    pct_change = df["close"].pct_change()
    flagged = pct_change[pct_change.abs() > threshold]
    warnings: list[str] = []
    for idx, pct in flagged.items():
        prev_close = df.loc[idx - 1, "close"]
        close_val = df.loc[idx, "close"]
        warnings.append(
            f"Possible unadjusted corporate action on {_as_date_str(df.loc[idx, 'date'])}: "
            f"close moved {pct:+.1%} ({prev_close:.2f} -> {close_val:.2f})."
        )
    return warnings


def _as_date_str(value: object) -> str:
    if hasattr(value, "date"):
        return str(value.date())
    return str(value)
