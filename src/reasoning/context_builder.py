"""
Builds minimal, token-efficient context for the causal reasoning LLM.

This is the second token optimization. Instead of sending raw PortfolioAnalysis
(with every field, every holding, every mutual fund detail), we extract ONLY
the data the LLM needs to build causal chains:
- Summary stats (total value, day change)
- Sector allocation (what they own)
- Top movers (what changed the most)
- Relevant news (already filtered)
- Market + sector context

This reduces the context from ~3000 tokens to ~800 tokens.
"""

from src.config import CONCENTRATION_RISK_THRESHOLD
from src.schemas import (
    ClassifiedNews,
    MarketSignal,
    PortfolioAnalysis,
    ReasoningContext,
    SectorTrends,
    
)


class ContextBuilder:
    def build(
        self,
        portfolio: PortfolioAnalysis,
        filtered_news: list[ClassifiedNews],
        market_signal: MarketSignal,
        sector_trends: SectorTrends,
    ) -> ReasoningContext:
        """
        Assembles the minimal structured payload the causal agent needs.

        The LLM needs just enough to:
        1. Understand what the user owns (summary + sector allocation)
        2. See how those holdings moved today (top movers)
        3. Connect movements to news and sector trends (filtered news + sector impacts)
        """
        portfolio_summary = _build_portfolio_summary(portfolio)
        sector_impacts = _build_sector_impacts(sector_trends)
        top_movers = _build_top_movers(portfolio)
        concentration_risks = _build_concentration_risks(portfolio)

        return ReasoningContext(
            portfolio_summary=portfolio_summary,
            relevant_news=filtered_news,
            sector_impacts=sector_impacts,
            top_movers=top_movers,
            market_sentiment=market_signal.sentiment,
            concentration_risks=concentration_risks,
        )


# Private helpers — each builds one slice of the ReasoningContext

def _build_portfolio_summary(portfolio: PortfolioAnalysis) -> dict:
    """Flat stat dict — no nested holding objects that bloat the payload."""
    return {
        "portfolio_id": portfolio.portfolio_id,
        "user_name": portfolio.user_name,
        "portfolio_type": portfolio.portfolio_type,
        "total_value": portfolio.total_value,
        "day_change_absolute": portfolio.day_change_absolute,
        "day_change_percent": portfolio.day_change_percent,
        "num_stocks": len(portfolio.stocks),
        "num_mutual_funds": len(portfolio.mutual_funds),
        "sector_allocation": portfolio.sector_allocation,
    }


def _build_sector_impacts(sector_trends: SectorTrends) -> dict[str, float]:
    """Maps each sector name to its average day-change % from live market data."""
    return {
        sector: trend.change_percent
        for sector, trend in sector_trends.trends.items()
    }


def _build_top_movers(portfolio: PortfolioAnalysis) -> list[dict]:
    """
    Returns the top 3 gainers and bottom 3 losers across all holdings.

    Stocks and mutual funds are treated equally — the LLM doesn't need to know
    the holding type to reason about why something moved.
    """
    all_holdings: list[dict] = []

    for stock in portfolio.stocks:
        all_holdings.append({
            "name": stock.name,
            "symbol": stock.symbol,
            "type": "stock",
            "sector": stock.sector,
            "weight": stock.weight_in_portfolio,
            "day_change_percent": stock.day_change_percent,
            "day_change_absolute": stock.day_change,
        })

    for mf in portfolio.mutual_funds:
        all_holdings.append({
            "name": mf.scheme_name,
            "code": mf.scheme_code,
            "type": "mutual_fund",
            "category": mf.category,
            "weight": mf.weight_in_portfolio,
            "day_change_percent": mf.day_change_percent,
            "day_change_absolute": mf.day_change,
        })

    if not all_holdings:
        return []

    sorted_holdings = sorted(all_holdings, key=lambda h: h["day_change_percent"], reverse=True)

    # Slice from both ends; duplicates are acceptable for small portfolios.
    gainers = sorted_holdings[:3]
    losers = sorted_holdings[-3:]
    # Preserve order: biggest gainer first, then biggest loser
    return gainers + losers


def _build_concentration_risks(portfolio: PortfolioAnalysis) -> list[str]:
    """Returns human-readable labels for sectors breaching the concentration threshold."""
    if not portfolio.concentration_risk:
        return []

    return [
        f"{sector} ({weight * 100:.1f}%)"
        for sector, weight in portfolio.sector_allocation.items()
        if weight > CONCENTRATION_RISK_THRESHOLD
    ]
