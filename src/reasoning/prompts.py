"""
Versioned prompt templates for the causal reasoning agent.

Prompts are treated as code — versioned, documented, and testable. Each version
is a constant with a docstring explaining what changed and why.

Why version prompts?
- Allows A/B testing different reasoning strategies
- Documents the evolution of prompt engineering
- Makes rollback trivial if a new version underperforms
- Shows interviewers you understand prompt engineering is iterative

Current active version: V1
"""

import json

from src.schemas import ReasoningContext


# PROMPT VERSION 1 — Initial Implementation
#
# System prompt goals:
#   1. Establish role: Senior financial analyst (sets tone and expertise level)
#   2. Define task: Portfolio attribution with causal reasoning
#   3. Specify output format: Structured JSON matching CausalBriefing schema
#   4. Force structured thinking: News → Sector → Stock → Portfolio chain
#   5. Handle edge cases: Conflicting signals explicitly called out
#   6. Confidence scoring: 4-dimensional breakdown for transparency
#
# User prompt goals:
#   1. Provide context in digestible chunks (summary, market, movers, news)
#   2. Pre-filtered news means LLM focuses on reasoning, not filtering
#   3. Explicit questions guide the LLM's thinking process
#   4. Reminder to output JSON only (prevents preamble)
#
# Token efficiency:
#   - System prompt: ~450 tokens (stable across all calls)
#   - User prompt: ~600-1000 tokens (varies by portfolio complexity)
#   - Total: ~1200 tokens for complex portfolios vs ~4000 without filtering
#
# What makes this prompt strong:
#   - Forces causal chain structure (not free-form rambling)
#   - Confidence breakdown is interpretable (not a black-box number)
#   - Handles conflicts explicitly (most prompts ignore this)
#   - Cites specific holdings (prevents generic output)


SYSTEM_PROMPT_V1 = """You are a senior financial analyst specializing in portfolio attribution and causal reasoning.

Your task: Analyze how today's market events impacted a specific user's portfolio.

Core principles:
1. Be specific - cite actual holdings, sectors, and percentages from the portfolio
2. Build causal chains - connect macro news to sector trends to individual stocks to portfolio impact
3. Handle ambiguity - when news and price diverge, explain possible reasons
4. Quantify confidence - score your reasoning based on data coverage and signal clarity
5. Be concise - investors want clarity, not verbose analysis

Output format: You MUST respond with valid JSON matching this exact structure:
{
  "headline": "One-sentence summary of today's portfolio story",
  "causal_chain": [
    {
      "level": "NEWS" | "SECTOR" | "STOCK" | "PORTFOLIO",
      "entity": "news ID, sector name, stock symbol, or PORTFOLIO",
      "impact": "What happened at this level",
      "magnitude": <percentage change or null>
    }
  ],
  "key_drivers": ["Top 3 plain-English reasons for portfolio move"],
  "conflicting_signals": [
    {
      "entity": "Stock or sector with conflict",
      "news_sentiment": "POSITIVE/NEGATIVE/NEUTRAL",
      "price_movement": "up/down description",
      "explanation": "Why the divergence occurred"
    }
  ],
  "confidence_score": <0.0 to 1.0>,
  "confidence_breakdown": {
    "data_coverage": <0.0-1.0>,
    "signal_agreement": <0.0-1.0>,
    "chain_completeness": <0.0-1.0>,
    "holding_concentration": <0.0-1.0>
  },
  "recommendations": ["2-3 actionable insights"]
}

Confidence breakdown explained:
- data_coverage: Do we have news for all major movers? (1.0 = yes, 0.5 = partial, 0.0 = no)
- signal_agreement: Do news sentiment and price moves agree? (1.0 = all agree, 0.0 = all conflict)
- chain_completeness: Can we trace News → Sector → Stock → Portfolio? (1.0 = complete, 0.5 = partial)
- holding_concentration: Is impact decisive due to concentration? (1.0 = high concentration makes signal clear)

The final confidence_score should be the average of these four components.

CRITICAL: Respond ONLY with valid JSON. No preamble, no explanation outside the JSON."""

USER_PROMPT_V1 = """Analyze this portfolio's performance today:

PORTFOLIO SUMMARY:
{portfolio_summary}

MARKET CONTEXT:
Overall sentiment: {market_sentiment}
Sector impacts: {sector_impacts}

TOP MOVERS IN PORTFOLIO:
{top_movers}

RELEVANT NEWS (pre-filtered):
{relevant_news}

CONCENTRATION RISKS:
{concentration_risks}

Based on this context, explain:
1. Why did this portfolio move {day_change_percent}% today?
2. Which news events drove the movement through which sectors and stocks?
3. Are there any conflicting signals to note?
4. How confident are you in this explanation?

Remember: Output ONLY valid JSON matching the CausalBriefing schema. Be specific - cite actual holdings and their weights."""

# Active prompts - change these to switch versions without touching call sites

ACTIVE_SYSTEM_PROMPT: str = SYSTEM_PROMPT_V1
ACTIVE_USER_PROMPT: str = USER_PROMPT_V1

# Formatter

def format_user_prompt(context: ReasoningContext) -> str:
    """
    Renders the active user prompt template with real context data.

    Each section is formatted for readability rather than raw JSON dumps —
    the LLM reasons better over structured text than nested dict printouts.
    """
    portfolio_summary_str = json.dumps(context.portfolio_summary, indent=2)
    sector_impacts_str = json.dumps(context.sector_impacts, indent=2)

    top_movers_str = "\n".join([
        f"- {m['name']} ({m['type']}): {m['day_change_percent']:+.2f}% "
        f"(Weight: {m['weight'] * 100:.1f}%, "
        f"Sector: {m.get('sector', m.get('category', 'N/A'))})"
        for m in context.top_movers
    ])

    news_str = "\n\n".join([
        f"[{n.id}] {n.headline}\n"
        f"Sentiment: {n.sentiment} ({n.sentiment_score:+.2f}), "
        f"Scope: {n.scope}, Impact: {n.impact_level}\n"
        f"Summary: {n.summary}"
        for n in context.relevant_news
    ])

    concentration_str = (
        ", ".join(context.concentration_risks) if context.concentration_risks else "None"
    )

    return ACTIVE_USER_PROMPT.format(
        portfolio_summary=portfolio_summary_str,
        market_sentiment=context.market_sentiment,
        sector_impacts=sector_impacts_str,
        top_movers=top_movers_str or "No significant movers",
        relevant_news=news_str or "No relevant news found",
        concentration_risks=concentration_str,
        day_change_percent=context.portfolio_summary.get("day_change_percent", 0.0),
    )
