"""
Type-safe data contracts enforcing structure at every module boundary in Causeway.

All inter-module data exchange uses these Pydantic models. If a module produces
data for another module, it returns one of these types — never a raw dict.
"""

from typing import Any, Literal
from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# MARKET INTELLIGENCE LAYER
# ---------------------------------------------------------------------------


class MarketSignal(BaseModel):
    """Aggregate market direction derived from index movements."""

    sentiment: Literal["BULLISH", "BEARISH", "NEUTRAL"]
    confidence: float = Field(..., ge=0.0, le=1.0, description="0–1 confidence in the sentiment call")
    indices_summary: dict[str, float] = Field(..., description="Index name → day-change %")
    reasoning: str = Field(..., description="Human-readable basis for the sentiment verdict")


class SectorTrend(BaseModel):
    """Performance summary for a single market sector."""

    sector_name: str
    change_percent: float = Field(..., description="Avg day-change % across sector constituents")
    sentiment: Literal["BULLISH", "BEARISH", "NEUTRAL"]
    top_movers: list[str] = Field(default_factory=list, description="Stock symbols with largest moves")
    stock_count: int = Field(..., description="Number of stocks analysed in this sector")


class SectorTrends(BaseModel):
    """Collection of sector trends for a single analysis run."""

    trends: dict[str, SectorTrend] = Field(..., description="Sector name → trend object")
    analysis_date: str = Field(..., description="ISO date string of the analysis")


# ---------------------------------------------------------------------------
# NEWS LAYER
# ---------------------------------------------------------------------------


class NewsEntity(BaseModel):
    """Structured entities extracted from a news item."""

    sectors: list[str] = Field(default_factory=list)
    stocks: list[str] = Field(default_factory=list)
    indices: list[str] = Field(default_factory=list)
    keywords: list[str] = Field(default_factory=list)


class ClassifiedNews(BaseModel):
    """A news item after sentiment classification and entity extraction."""

    id: str
    headline: str
    summary: str
    sentiment: Literal["POSITIVE", "NEGATIVE", "NEUTRAL", "MIXED"]
    sentiment_score: float = Field(..., ge=-1.0, le=1.0)
    scope: Literal["MARKET_WIDE", "SECTOR_SPECIFIC", "STOCK_SPECIFIC"]
    impact_level: Literal["HIGH", "MEDIUM", "LOW"]
    entities: NewsEntity
    published_at: str = Field(..., description="ISO datetime string")
    relevance_score: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description="Set by the relevance filter based on portfolio overlap",
    )


# ---------------------------------------------------------------------------
# PORTFOLIO LAYER
# ---------------------------------------------------------------------------


class StockHolding(BaseModel):
    """One equity position in a portfolio."""

    symbol: str
    name: str
    sector: str
    quantity: int
    avg_buy_price: float
    current_price: float
    investment_value: float = Field(..., description="Cost basis: quantity × avg_buy_price")
    current_value: float = Field(..., description="Mark-to-market: quantity × current_price")
    gain_loss: float
    gain_loss_percent: float
    day_change: float = Field(..., description="Absolute INR change today")
    day_change_percent: float
    weight_in_portfolio: float = Field(..., ge=0.0, le=1.0, description="Fraction of total portfolio value")


class MutualFundHolding(BaseModel):
    """One mutual fund position in a portfolio."""

    scheme_code: str
    scheme_name: str
    category: str
    units: float
    avg_nav: float
    current_nav: float
    investment_value: float
    current_value: float
    gain_loss: float
    gain_loss_percent: float
    day_change: float
    day_change_percent: float
    weight_in_portfolio: float = Field(..., ge=0.0, le=1.0)


class PortfolioAnalysis(BaseModel):
    """Full analytics output for one portfolio, merging equity and MF positions."""

    portfolio_id: str
    user_name: str
    portfolio_type: str
    total_value: float
    day_change_absolute: float
    day_change_percent: float
    stocks: list[StockHolding] = Field(default_factory=list)
    mutual_funds: list[MutualFundHolding] = Field(default_factory=list)
    sector_allocation: dict[str, float] = Field(
        default_factory=dict,
        description="Sector name → fraction of total portfolio value",
    )
    concentration_risk: bool = Field(
        default=False,
        description="True when any sector exceeds CONCENTRATION_RISK_THRESHOLD",
    )
    concentration_details: str | None = Field(default=None)
    top_gainer: dict[str, Any] | None = Field(default=None, description="Holding with highest day_change_percent")
    top_loser: dict[str, Any] | None = Field(default=None, description="Holding with lowest day_change_percent")


# ---------------------------------------------------------------------------
# REASONING LAYER
# ---------------------------------------------------------------------------


class CausalLink(BaseModel):
    """One hop in the causal chain: News → Sector → Stock → Portfolio."""

    level: Literal["NEWS", "SECTOR", "STOCK", "PORTFOLIO"]
    entity: str = Field(..., description="News ID, sector name, stock symbol, or 'PORTFOLIO'")
    impact: str = Field(..., description="Natural-language description of what happened at this level")
    magnitude: float | None = Field(default=None, description="Quantified % change if available")


class ConflictingSignal(BaseModel):
    """A case where news sentiment and observed price movement disagree."""

    entity: str = Field(..., description="Stock symbol or sector name with the conflict")
    news_sentiment: str
    price_movement: str
    explanation: str = Field(..., description="Hypothesis for why the divergence occurred")


class CausalBriefing(BaseModel):
    """Structured LLM output — the final deliverable of the causal agent."""

    headline: str = Field(..., description="One-sentence summary of today's portfolio story")
    causal_chain: list[CausalLink] = Field(..., description="Ordered hops: News → Sector → Stock → Portfolio")
    key_drivers: list[str] = Field(..., description="Top 3 plain-English reasons for the portfolio move")
    conflicting_signals: list[ConflictingSignal] = Field(default_factory=list)
    confidence_score: float = Field(..., ge=0.0, le=1.0, description="Aggregate confidence across all dimensions")
    confidence_breakdown: dict[str, float] = Field(
        ...,
        description="Per-dimension scores: data_coverage, signal_agreement, chain_completeness, holding_concentration",
    )
    recommendations: list[str] = Field(..., description="2–3 actionable insights for the investor")


class ReasoningContext(BaseModel):
    """Minimal, token-efficient payload assembled by ContextBuilder and sent to the LLM."""

    portfolio_summary: dict[str, Any] = Field(..., description="Flattened portfolio stats — no raw position lists")
    relevant_news: list[ClassifiedNews] = Field(..., description="Pre-filtered to ~5 items by relevance filter")
    sector_impacts: dict[str, float] = Field(..., description="Sector name → day-change %")
    top_movers: list[dict[str, Any]] = Field(..., description="Top gaining and losing holdings")
    market_sentiment: str = Field(..., description="BULLISH / BEARISH / NEUTRAL")
    concentration_risks: list[str] = Field(default_factory=list, description="Sectors breaching concentration threshold")


# ---------------------------------------------------------------------------
# EVALUATION LAYER
# ---------------------------------------------------------------------------


class EvaluationResult(BaseModel):
    """Self-grader output assessing the quality of a CausalBriefing."""

    overall_score: float = Field(..., ge=0.0, le=10.0)
    dimension_scores: dict[str, float] = Field(
        ...,
        description="causal_depth, specificity, hedging_quality, portfolio_grounded — each 0–10",
    )
    rule_checks: dict[str, bool] = Field(
        ...,
        description="Structural checks, e.g. 'cites_actual_holdings', 'chain_has_four_levels'",
    )
    llm_feedback: str = Field(..., description="Short LLM critique of the briefing quality")
    passed: bool = Field(..., description="True when overall_score ≥ MIN_CONFIDENCE_SCORE × 10")
