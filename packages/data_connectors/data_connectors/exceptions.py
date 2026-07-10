"""Shared exception types for data_connectors.

Kept separate from ``data_connectors.validation.DataValidationError`` so
callers can distinguish two different failure modes:

- ``DataFetchError`` (this module): the *provider* failed -- network error,
  invalid/delisted symbol, empty response, missing optional dependency, etc.
- ``DataValidationError`` (``data_connectors.validation``): the provider
  *returned* data, but it violates the OHLCV contract (bad columns, NaNs
  that shouldn't be there, high < low, etc).

``CacheError`` covers the local on-disk cache (``data_connectors.cache``)
detecting an internal inconsistency, e.g. a filename-sanitization collision
between two different symbols.
"""

from __future__ import annotations


class DataFetchError(RuntimeError):
    """Raised when a connector fails to fetch data from its provider."""


class CacheError(RuntimeError):
    """Raised when the local OHLCV cache detects an internal inconsistency."""
