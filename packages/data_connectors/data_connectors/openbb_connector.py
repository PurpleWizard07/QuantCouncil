"""OpenBB connector placeholder (INACTIVE in v1).

Registered in ``data_connectors.registry.get_connector`` under the name
"openbb" so the factory shape is in place for a future phase, but
``fetch_daily`` is intentionally unimplemented. The `openbb` SDK pulls a
large, broad dependency tree (covering many asset classes and providers well
beyond this project's free-data, NIFTY-50-daily-only scope); integrating it
now isn't worth the install cost when ``YFinanceConnector`` already covers
everything Phase 2 needs. This class exists purely so the connector
interface is demonstrably swappable and so a future phase has an obvious
place to add the real implementation.
"""

from __future__ import annotations

from datetime import date

import pandas as pd

from data_connectors.base import OHLCVConnector


class OpenBBConnector(OHLCVConnector):
    """Placeholder ``OHLCVConnector`` for the OpenBB Platform (inactive)."""

    def fetch_daily(self, symbol: str, start: date, end: date) -> pd.DataFrame:
        """Not implemented -- see module docstring.

        Raises:
            NotImplementedError: Always. Use
                ``get_connector("yfinance")`` instead; that is the active
                Phase 2 connector.
        """
        raise NotImplementedError(
            "OpenBBConnector is a registered placeholder, not an active "
            "connector, in QuantCouncil v1. The active Phase 2 connector is "
            "YFinanceConnector (data_connectors.yfinance_connector); OpenBB "
            "integration is deferred because its SDK's install footprint "
            "isn't worth the cost for this project's scope. Use "
            "get_connector('yfinance') instead."
        )
