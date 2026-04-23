"""
Groups stocks by sector and computes per-sector performance summaries.

Sits after MarketAnalyzer in the Market Intelligence Layer. Produces SectorTrends
that tell downstream modules which sectors are driving or dragging the market today.
"""

import datetime
from src.config import BULLISH_THRESHOLD, BEARISH_THRESHOLD
from src.schemas import SectorTrend, SectorTrends


class SectorAnalyzer:
    def __init__(self, sector_mapping: dict) -> None:
        """
        Args:
            sector_mapping: Parsed contents of sector_mapping.json.
        """
        self._sectors: dict[str, list[str]] = {
            name: info["stocks"]
            for name, info in sector_mapping.get("sectors", {}).items()
        }

    def analyze(self, stocks: dict[str, dict]) -> SectorTrends:
        """
        Computes average performance and sentiment for each sector.

        Logic per sector:
        - Collect stocks present in both sector_mapping and the provided stocks dict
        - Average their change_percent values
        - Apply BULLISH/BEARISH/NEUTRAL thresholds (same as MarketAnalyzer)
        - Pick top 3 movers by absolute change_percent
        """
        trends: dict[str, SectorTrend] = {}

        for sector_name, sector_symbols in self._sectors.items():
            # Only analyse stocks we actually have price data for
            present = [sym for sym in sector_symbols if sym in stocks]
            if not present:
                continue

            changes: list[tuple[str, float]] = []
            for sym in present:
                stock = stocks[sym]
                if "change_percent" not in stock:
                    raise ValueError(f"Stock '{sym}' is missing 'change_percent'")
                changes.append((sym, float(stock["change_percent"])))

            avg_change = sum(pct for _, pct in changes) / len(changes)

            if avg_change >= BULLISH_THRESHOLD:
                sentiment = "BULLISH"
            elif avg_change <= BEARISH_THRESHOLD:
                sentiment = "BEARISH"
            else:
                sentiment = "NEUTRAL"

            top_movers = [
                sym for sym, _ in sorted(changes, key=lambda x: abs(x[1]), reverse=True)[:3]
            ]

            trends[sector_name] = SectorTrend(
                sector_name=sector_name,
                change_percent=round(avg_change, 4),
                sentiment=sentiment,
                top_movers=top_movers,
                stock_count=len(present),
            )

        return SectorTrends(
            trends=trends,
            analysis_date=datetime.datetime.now().isoformat(),
        )
