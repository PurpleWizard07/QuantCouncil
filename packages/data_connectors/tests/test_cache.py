"""Tests for OHLCVCache and CachedConnector, using tmp_path -- no network."""

from __future__ import annotations

from datetime import date
from pathlib import Path

import pandas as pd
import pytest

from data_connectors.base import OHLCVConnector
from data_connectors.cache import CachedConnector, OHLCVCache
from data_connectors.exceptions import CacheError


def _df(dates: list[str], start_val: float = 100.0) -> pd.DataFrame:
    parsed = pd.to_datetime(dates)
    n = len(parsed)
    return pd.DataFrame(
        {
            "date": parsed,
            "open": [start_val + i for i in range(n)],
            "high": [start_val + i + 2 for i in range(n)],
            "low": [start_val + i - 2 for i in range(n)],
            "close": [start_val + i + 1 for i in range(n)],
            "volume": [1000 + i for i in range(n)],
        }
    )


class _CountingConnector(OHLCVConnector):
    """Fake connector that counts calls and returns a fixed 10-day frame."""

    def __init__(self) -> None:
        self.calls: list[tuple[str, date, date]] = []

    def fetch_daily(self, symbol: str, start: date, end: date) -> pd.DataFrame:
        self.calls.append((symbol, start, end))
        dates = pd.date_range("2024-01-01", periods=10, freq="D")
        return pd.DataFrame(
            {
                "date": dates,
                "open": [100.0] * 10,
                "high": [102.0] * 10,
                "low": [98.0] * 10,
                "close": [101.0] * 10,
                "volume": [1000] * 10,
            }
        )


# --- OHLCVCache: filename sanitization -------------------------------------


@pytest.mark.parametrize(
    "symbol,expected_stem",
    [
        ("M&M", "M_M"),
        ("BAJAJ-AUTO", "BAJAJ_AUTO"),
        ("RELIANCE", "RELIANCE"),
    ],
)
def test_path_for_sanitizes_filesystem_unsafe_symbols(
    tmp_path: Path, symbol: str, expected_stem: str
) -> None:
    cache = OHLCVCache(cache_dir=tmp_path)
    path = cache.path_for(symbol)
    assert path.name == f"{expected_stem}.parquet"
    assert path.parent == tmp_path


# --- OHLCVCache: put/get round trip -----------------------------------------


def test_put_then_get_returns_identical_data(tmp_path: Path) -> None:
    cache = OHLCVCache(cache_dir=tmp_path)
    df = _df(["2024-01-01", "2024-01-02", "2024-01-03"])
    cache.put("RELIANCE", df)

    out = cache.get("RELIANCE", date(2024, 1, 1), date(2024, 1, 3))
    assert out is not None
    assert list(out.columns) == ["date", "open", "high", "low", "close", "volume"]
    assert len(out) == 3
    pd.testing.assert_series_equal(
        out["close"].reset_index(drop=True), df["close"].reset_index(drop=True)
    )


def test_get_returns_none_when_no_cache_file(tmp_path: Path) -> None:
    cache = OHLCVCache(cache_dir=tmp_path)
    assert cache.get("RELIANCE", date(2024, 1, 1), date(2024, 1, 3)) is None


def test_get_returns_none_on_partial_coverage(tmp_path: Path) -> None:
    cache = OHLCVCache(cache_dir=tmp_path)
    df = _df(["2024-01-05", "2024-01-06", "2024-01-07"])
    cache.put("RELIANCE", df)

    # Requested range starts before the cached range -> not fully covered.
    assert cache.get("RELIANCE", date(2024, 1, 1), date(2024, 1, 7)) is None
    # Requested range ends after the cached range -> not fully covered.
    assert cache.get("RELIANCE", date(2024, 1, 5), date(2024, 1, 10)) is None
    # Fully inside -> covered.
    assert cache.get("RELIANCE", date(2024, 1, 5), date(2024, 1, 6)) is not None


def test_get_treats_max_date_past_end_as_covering(tmp_path: Path) -> None:
    """A cache file extending past the requested end still covers it, even
    if `end` itself is a non-trading day with no bar."""
    cache = OHLCVCache(cache_dir=tmp_path)
    df = _df(["2024-01-01", "2024-01-02", "2024-01-08"])  # gap over a weekend
    cache.put("RELIANCE", df)

    # 2024-01-06 (a Saturday) has no bar, but max cached date (01-08) >= it.
    out = cache.get("RELIANCE", date(2024, 1, 1), date(2024, 1, 6))
    assert out is not None


def test_put_merges_and_dedups_keeping_newest(tmp_path: Path) -> None:
    cache = OHLCVCache(cache_dir=tmp_path)
    original = _df(["2024-01-01", "2024-01-02"], start_val=100.0)
    cache.put("RELIANCE", original)

    updated = _df(["2024-01-02", "2024-01-03"], start_val=500.0)
    cache.put("RELIANCE", updated)

    out = cache.get("RELIANCE", date(2024, 1, 1), date(2024, 1, 3))
    assert out is not None
    assert len(out) == 3
    # 2024-01-02 must reflect the newest write (start_val=500 -> open=500.0),
    # not the original (open=101.0).
    row = out.loc[out["date"] == pd.Timestamp("2024-01-02")].iloc[0]
    assert row["open"] == 500.0


def test_put_writes_atomically_no_leftover_tmp_file(tmp_path: Path) -> None:
    cache = OHLCVCache(cache_dir=tmp_path)
    cache.put("RELIANCE", _df(["2024-01-01"]))
    leftovers = list(tmp_path.glob("*.tmp"))
    assert leftovers == []
    assert cache.path_for("RELIANCE").is_file()


def test_filename_sanitization_collision_is_detected(tmp_path: Path) -> None:
    cache = OHLCVCache(cache_dir=tmp_path)
    cache.put("M&M", _df(["2024-01-01"]))

    # A different symbol that happens to sanitize to the same filename stem
    # must not be silently merged into M&M's file.
    with pytest.raises(CacheError):
        cache.put("M_M", _df(["2024-01-02"]))


# --- CachedConnector ---------------------------------------------------------


def test_cached_connector_serves_from_cache_without_calling_connector(tmp_path: Path) -> None:
    cache = OHLCVCache(cache_dir=tmp_path)
    cache.put("RELIANCE", _df([f"2024-01-{d:02d}" for d in range(1, 11)]))

    connector = _CountingConnector()
    cached_connector = CachedConnector(connector, cache)

    out = cached_connector.get_ohlcv("RELIANCE", "2024-01-02", "2024-01-05")
    assert len(connector.calls) == 0
    assert len(out) == 4


def test_cached_connector_fetches_on_miss_and_populates_cache(tmp_path: Path) -> None:
    cache = OHLCVCache(cache_dir=tmp_path)
    connector = _CountingConnector()
    cached_connector = CachedConnector(connector, cache)

    out = cached_connector.get_ohlcv("RELIANCE", "2024-01-01", "2024-01-05")
    assert len(connector.calls) == 1
    assert len(out) == 5
    assert out["date"].min() == pd.Timestamp("2024-01-01")
    assert out["date"].max() == pd.Timestamp("2024-01-05")

    # A second call for the same, now-cached range must not hit the connector again.
    out2 = cached_connector.get_ohlcv("RELIANCE", "2024-01-01", "2024-01-05")
    assert len(connector.calls) == 1
    assert len(out2) == 5


def test_cached_connector_refresh_true_always_refetches(tmp_path: Path) -> None:
    cache = OHLCVCache(cache_dir=tmp_path)
    cache.put("RELIANCE", _df([f"2024-01-{d:02d}" for d in range(1, 11)]))

    connector = _CountingConnector()
    cached_connector = CachedConnector(connector, cache, refresh=True)

    out = cached_connector.get_ohlcv("RELIANCE", "2024-01-01", "2024-01-05")
    assert len(connector.calls) == 1
    assert len(out) == 5


def test_cached_connector_validates_inputs_like_get_ohlcv(tmp_path: Path) -> None:
    cache = OHLCVCache(cache_dir=tmp_path)
    connector = _CountingConnector()
    cached_connector = CachedConnector(connector, cache)

    with pytest.raises(ValueError, match="daily"):
        cached_connector.get_ohlcv("RELIANCE", "2024-01-01", "2024-01-05", timeframe="1h")
    with pytest.raises(ValueError, match="on or before"):
        cached_connector.get_ohlcv("RELIANCE", "2024-01-05", "2024-01-01")
    assert len(connector.calls) == 0
