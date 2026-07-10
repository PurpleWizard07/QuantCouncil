"""Local DuckDB/Parquet cache for OHLCV data.

One Parquet file per symbol under ``<repo_root>/data/processed/ohlcv/`` by
default. ``OHLCVCache`` provides low-level ``get``/``put`` operations;
``CachedConnector`` wraps any ``OHLCVConnector`` so downstream code gets
transparent caching behind the exact same ``get_ohlcv`` interface.

Coverage heuristic (documented v1 simplification): whether a cached file
"covers" a requested ``[start, end]`` range is decided from the file's
min/max cached ``date`` -- if ``min(date) <= start`` and ``max(date) >=
end``, we serve from cache; otherwise we treat it as a miss and re-fetch.
Exact trading-calendar coverage (e.g. distinguishing "no bar because it's a
holiday" from "no bar because we never fetched it") is not tracked. In
particular, a file whose max cached date is already ``>= end`` counts as
covering even when ``end`` itself falls on a weekend/holiday with no bar --
we do not re-fetch just to confirm a date that could never have a bar. The
same reasoning applies (less precisely) to the ``start`` side: if the
requested ``start`` is a non-trading day earlier than any cached bar, the
containment check can under-cover and trigger a redundant re-fetch. That is
an accepted asymmetry, not a correctness bug -- a redundant re-fetch merges
harmlessly back into the same file.
"""

from __future__ import annotations

import re
from datetime import date, datetime
from pathlib import Path

import duckdb
import pandas as pd

from data_connectors.base import OHLCVConnector, _validate_get_ohlcv_args
from data_connectors.exceptions import CacheError

_SANITIZE_PATTERN = re.compile(r"[^A-Za-z0-9]")


def _default_cache_dir() -> Path:
    """Best-effort resolution of ``<repo_root>/data/processed/ohlcv``.

    Walks up from this file looking for a directory that has sibling
    ``data/`` and ``packages/`` directories (the repo root marker), the same
    style of heuristic used by ``data_connectors.universe``. Falls back to
    a fixed relative offset (this file lives at
    ``<repo_root>/packages/data_connectors/data_connectors/cache.py``) if
    that marker isn't found, so this still works even if invoked from an
    unusual working directory.
    """
    here = Path(__file__).resolve()
    for parent in [here.parent, *here.parents]:
        if (parent / "data").is_dir() and (parent / "packages").is_dir():
            return parent / "data" / "processed" / "ohlcv"
    return here.parents[3] / "data" / "processed" / "ohlcv"


def _sanitize_filename(symbol: str) -> str:
    """Map a symbol to a filesystem-safe filename stem.

    Windows disallows or discourages several characters that appear in NSE
    symbols (e.g. "&" in "M&M", "-" is fine but kept consistent anyway);
    every non-alphanumeric character is replaced with "_". This mapping is
    many-to-one in theory, so it is not trusted blindly: the true symbol is
    also stored as a column inside the Parquet file, and both ``get`` and
    ``put`` verify it matches before trusting the file's contents (see
    ``CacheError``). In practice, no two symbols in the NIFTY 50 universe
    collide under this scheme.
    """
    return _SANITIZE_PATTERN.sub("_", symbol)


def _to_date(value: object) -> date:
    """Normalize a DuckDB/pandas timestamp-ish value to a plain ``date``."""
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    return pd.Timestamp(value).date()


class OHLCVCache:
    """Local Parquet-backed OHLCV cache, queried via DuckDB.

    Args:
        cache_dir: Directory holding one ``<sanitized_symbol>.parquet`` file
            per symbol. Defaults to ``<repo_root>/data/processed/ohlcv``.
            Created if it doesn't exist.
    """

    def __init__(self, cache_dir: Path | None = None) -> None:
        self.cache_dir = Path(cache_dir) if cache_dir is not None else _default_cache_dir()
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def path_for(self, symbol: str) -> Path:
        """Return the Parquet file path used to cache ``symbol``."""
        return self.cache_dir / f"{_sanitize_filename(symbol)}.parquet"

    def get(self, symbol: str, start: date, end: date) -> pd.DataFrame | None:
        """Return cached bars for ``[start, end]`` if fully covered.

        Args:
            symbol: Plain NSE symbol.
            start: Range start (inclusive).
            end: Range end (inclusive).

        Returns:
            A DataFrame with columns ``[date, open, high, low, close,
            volume]`` sliced to ``[start, end]``, or ``None`` if there is no
            cache file yet, or the cached range does not fully cover
            ``[start, end]`` (see the module docstring's coverage
            heuristic).

        Raises:
            CacheError: If the cache file's stored symbol doesn't match
                ``symbol`` (a filename-sanitization collision).
        """
        path = self.path_for(symbol)
        if not path.is_file():
            return None

        con = duckdb.connect()
        try:
            bounds = con.execute(
                "SELECT min(date), max(date), min(symbol), max(symbol) "
                "FROM read_parquet(?)",
                [str(path)],
            ).fetchone()
        finally:
            con.close()

        if bounds is None or bounds[0] is None:
            return None
        min_date, max_date, min_symbol, max_symbol = bounds
        if min_symbol != max_symbol or min_symbol != symbol:
            raise CacheError(
                f"Cache file {path} (for filename-sanitized symbol "
                f"{_sanitize_filename(symbol)!r}) contains data for a "
                f"different symbol ({min_symbol!r}/{max_symbol!r}) than "
                f"requested ({symbol!r}); this indicates a filename "
                "sanitization collision between two different symbols."
            )

        if _to_date(min_date) > start or _to_date(max_date) < end:
            return None

        con = duckdb.connect()
        try:
            df = con.execute(
                "SELECT date, open, high, low, close, volume FROM "
                "read_parquet(?) WHERE date BETWEEN ? AND ? ORDER BY date",
                [str(path), start, end],
            ).fetchdf()
        finally:
            con.close()

        df["date"] = pd.to_datetime(df["date"])
        return df

    def put(self, symbol: str, df: pd.DataFrame) -> None:
        """Merge ``df`` into the on-disk cache file for ``symbol``.

        Existing rows (if any) are concatenated with the new rows,
        duplicate dates are dropped keeping the *newest* value (``df``'s
        rows win over what was already on disk, since a fresh fetch is more
        likely to reflect corrected data), the result is sorted ascending
        by date, and written atomically: to a temp file first, then an
        OS-level replace, so a crash mid-write can never leave a truncated
        or corrupted cache file.

        Args:
            symbol: Plain NSE symbol.
            df: OHLCV frame to merge in; expected to already satisfy the
                ``OHLCVConnector`` contract (e.g. the output of
                ``get_ohlcv``).

        Raises:
            CacheError: If the existing cache file belongs to a different
                symbol (a filename-sanitization collision).
        """
        path = self.path_for(symbol)
        to_write = df.copy()
        to_write["date"] = pd.to_datetime(to_write["date"])
        to_write["symbol"] = symbol

        if path.is_file():
            existing = pd.read_parquet(path)
            if not existing.empty and "symbol" in existing.columns:
                existing_symbols = existing["symbol"].unique()
                if len(existing_symbols) > 1 or existing_symbols[0] != symbol:
                    raise CacheError(
                        f"Cache file {path} already holds data for a "
                        f"different symbol ({list(existing_symbols)!r}) than "
                        f"{symbol!r}; refusing to merge to avoid mixing "
                        "two symbols' data (filename sanitization collision)."
                    )
            existing["date"] = pd.to_datetime(existing["date"])
            combined = pd.concat([existing, to_write], ignore_index=True)
        else:
            combined = to_write

        combined = combined.drop_duplicates(subset="date", keep="last")
        combined = combined.sort_values("date").reset_index(drop=True)

        tmp_path = path.with_name(path.name + ".tmp")
        combined.to_parquet(tmp_path, index=False)
        tmp_path.replace(path)


class CachedConnector:
    """Wraps an ``OHLCVConnector`` with a local Parquet/DuckDB cache.

    Implements the same ``get_ohlcv(symbol, start_date, end_date,
    timeframe="1d")`` signature as ``OHLCVConnector``, so it is a drop-in
    replacement for callers that just want caching transparently applied.

    On a cache hit (per ``OHLCVCache``'s coverage heuristic), the wrapped
    connector is not called at all. On a miss -- or whenever ``refresh`` is
    True -- the request is delegated to the wrapped connector, the fetched
    frame is merged into the cache, and the requested ``[start, end]`` slice
    of that freshly-fetched frame is returned directly (not re-read from the
    cache), so the response isn't at the mercy of the same weekend/holiday
    edge case documented on ``OHLCVCache``.

    Args:
        connector: The underlying ``OHLCVConnector`` to fetch from on a miss.
        cache: The ``OHLCVCache`` to read from and write into.
        refresh: When True, always re-fetch from ``connector`` and merge the
            result into the cache instead of trusting what's on disk. Useful
            for explicitly refreshing a range (e.g. the most recent days,
            which can be revised).
    """

    def __init__(
        self, connector: OHLCVConnector, cache: OHLCVCache, refresh: bool = False
    ) -> None:
        self.connector = connector
        self.cache = cache
        self.refresh = refresh

    def get_ohlcv(
        self,
        symbol: str,
        start_date: date | str,
        end_date: date | str,
        timeframe: str = "1d",
    ) -> pd.DataFrame:
        """Serve ``[start_date, end_date]`` from cache, or fetch and cache it.

        Args, returns, and raises mirror ``OHLCVConnector.get_ohlcv``.
        """
        start, end = _validate_get_ohlcv_args(start_date, end_date, timeframe)

        if not self.refresh:
            cached = self.cache.get(symbol, start, end)
            if cached is not None:
                return cached

        fresh = self.connector.get_ohlcv(symbol, start, end, timeframe=timeframe)
        self.cache.put(symbol, fresh)

        mask = (fresh["date"] >= pd.Timestamp(start)) & (fresh["date"] <= pd.Timestamp(end))
        return fresh.loc[mask].reset_index(drop=True)
