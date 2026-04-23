"""
Analyzes index movements to determine overall market sentiment.

This is the first stage of the Market Intelligence Layer. It reads raw index data
and produces a single MarketSignal that downstream modules use to contextualize
portfolio movements.
"""

from src.config import BULLISH_THRESHOLD, BEARISH_THRESHOLD
from src.schemas import MarketSignal


class MarketAnalyzer:
    def analyze(self, indices: dict[str, dict]) -> MarketSignal:
        """
        Determines market sentiment from index day-change percentages.

        Logic:
        - Extract change_percent for each index
        - Average across all indices
        - BULLISH if avg >= BULLISH_THRESHOLD, BEARISH if avg <= BEARISH_THRESHOLD
        - Confidence = fraction of indices that agree with the verdict
        """
        if not indices:
            return MarketSignal(
                sentiment="NEUTRAL",
                confidence=0.0,
                indices_summary={},
                reasoning="No index data available.",
            )

        summary: dict[str, float] = {}
        for symbol, data in indices.items():
            if "change_percent" not in data:
                raise ValueError(f"Index '{symbol}' is missing 'change_percent'")
            summary[symbol] = float(data["change_percent"])

        avg_change = sum(summary.values()) / len(summary)

        if avg_change >= BULLISH_THRESHOLD:
            sentiment = "BULLISH"
        elif avg_change <= BEARISH_THRESHOLD:
            sentiment = "BEARISH"
        else:
            sentiment = "NEUTRAL"

        # Confidence: share of indices whose own change aligns with the verdict
        agreeing = sum(
            1 for pct in summary.values()
            if (sentiment == "BULLISH" and pct >= BULLISH_THRESHOLD)
            or (sentiment == "BEARISH" and pct <= BEARISH_THRESHOLD)
            or (sentiment == "NEUTRAL" and BEARISH_THRESHOLD < pct < BULLISH_THRESHOLD)
        )
        confidence = round(agreeing / len(summary), 2)

        # Build a readable summary of each index for the reasoning string
        index_parts = []
        for symbol, pct in summary.items():
            name = indices[symbol].get("name", symbol)
            direction = "up" if pct >= 0 else "down"
            index_parts.append(f"{name} {direction} {abs(pct):.2f}%")

        reasoning = (
            f"Market sentiment is {sentiment} with {int(confidence * 100)}% confidence. "
            + ", ".join(index_parts)
            + "."
        )

        return MarketSignal(
            sentiment=sentiment,
            confidence=confidence,
            indices_summary=summary,
            reasoning=reasoning,
        )
