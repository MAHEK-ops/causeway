"""
Evaluation rubric defining what makes a high-quality causal briefing.

Two types of checks:
1. Rule-based (deterministic): Does it cite actual holdings? Does it have all four levels?
2. LLM-based (subjective): How deep is the reasoning? How specific are the claims?

Rule checks are fast and reliable — they verify structural correctness.
LLM checks assess quality dimensions that rules can't capture.

This hybrid approach is more reliable than pure LLM grading (which can be
inconsistent) and more nuanced than pure rule-based grading (which misses quality).
"""

from src.schemas import CausalBriefing, PortfolioAnalysis

# ---------------------------------------------------------------------------
# Dimension names
# ---------------------------------------------------------------------------

# Dimensions the LLM grader scores on a 1-10 scale
LLM_DIMENSIONS: list[str] = [
    "causal_depth",       # How well does it trace News → Sector → Stock → Portfolio?
    "specificity",        # Does it cite actual holdings, sectors, percentages?
    "hedging_quality",    # Does it acknowledge uncertainty appropriately?
    "portfolio_grounded", # Are claims backed by actual portfolio data?
]

# Rule-based checks (pass/fail) — each maps to a function below
RULE_CHECKS: list[str] = [
    "cites_actual_holdings",   # Does causal chain reference real stock symbols?
    "chain_has_four_levels",   # Does it have NEWS, SECTOR, STOCK, PORTFOLIO levels?
    "confidence_is_justified", # Is confidence score consistent with breakdown avg?
    "recommendations_present", # Are there 2-3 recommendations?
]


# ---------------------------------------------------------------------------
# Individual rule-check functions
# ---------------------------------------------------------------------------

def check_cites_actual_holdings(
    briefing: CausalBriefing,
    portfolio: PortfolioAnalysis,
) -> tuple[bool, str]:
    """
    Verifies the causal chain references actual stocks or sectors from the portfolio.

    A good briefing cites specific holdings, not generic sector statements.
    Matching on either stock symbols OR sector names counts as a pass —
    sector-heavy portfolios (e.g. mostly MFs) may not have individual stock mentions.
    """
    portfolio_symbols = {h.symbol for h in portfolio.stocks}
    portfolio_sectors = set(portfolio.sector_allocation.keys())

    cited_entities = {link.entity for link in briefing.causal_chain}

    stock_matches = cited_entities & portfolio_symbols
    sector_matches = cited_entities & portfolio_sectors

    if stock_matches or sector_matches:
        return (
            True,
            f"Cites {len(stock_matches)} stock(s) and {len(sector_matches)} sector(s) from portfolio",
        )
    return False, "Causal chain does not reference any actual holdings or sectors"


def check_chain_has_four_levels(
    briefing: CausalBriefing,
    portfolio: PortfolioAnalysis,  # noqa: ARG001 — kept for uniform signature
) -> tuple[bool, str]:
    """
    Verifies the causal chain includes all four levels: NEWS, SECTOR, STOCK, PORTFOLIO.

    A complete chain traces the full causal path from macro event down to
    portfolio-level impact. Missing any level means the reasoning has a gap.
    """
    levels_present = {link.level for link in briefing.causal_chain}
    required_levels = {"NEWS", "SECTOR", "STOCK", "PORTFOLIO"}

    missing = required_levels - levels_present
    if not missing:
        return True, "All four causal levels present"
    return False, f"Missing levels: {', '.join(sorted(missing))}"


def check_confidence_is_justified(
    briefing: CausalBriefing,
    portfolio: PortfolioAnalysis,  # noqa: ARG001 — kept for uniform signature
) -> tuple[bool, str]:
    """
    Verifies the overall confidence score is roughly the average of its components.

    The system prompt instructs the LLM to average the four breakdown scores.
    A large deviation means the LLM either ignored the instruction or made an
    arithmetic error — both reduce trust in the confidence signal.
    """
    breakdown = briefing.confidence_breakdown
    if not breakdown:
        return False, "Confidence breakdown is empty"

    avg = sum(breakdown.values()) / len(breakdown)
    delta = abs(briefing.confidence_score - avg)

    if delta <= 0.15:
        return (
            True,
            f"Confidence {briefing.confidence_score:.2f} matches breakdown avg {avg:.2f} (Δ={delta:.2f})",
        )
    return (
        False,
        f"Confidence {briefing.confidence_score:.2f} diverges from breakdown avg {avg:.2f} (Δ={delta:.2f})",
    )


def check_recommendations_present(
    briefing: CausalBriefing,
    portfolio: PortfolioAnalysis,  # noqa: ARG001 — kept for uniform signature
) -> tuple[bool, str]:
    """
    Verifies the briefing includes between 2 and 3 actionable recommendations.

    Fewer than 2 suggests the LLM ran out of things to say;
    more than 3 dilutes the signal — investors want a focused action list.
    """
    n = len(briefing.recommendations)
    if 2 <= n <= 3:
        return True, f"{n} recommendation(s) provided"
    if n > 3:
        return False, f"Too many recommendations ({n}) — should be 2–3"
    return False, f"Too few recommendations ({n}) — should be 2–3"


# ---------------------------------------------------------------------------
# Aggregate runner
# ---------------------------------------------------------------------------

_RULE_FUNCTIONS = {
    "cites_actual_holdings":   check_cites_actual_holdings,
    "chain_has_four_levels":   check_chain_has_four_levels,
    "confidence_is_justified": check_confidence_is_justified,
    "recommendations_present": check_recommendations_present,
}


def run_rule_checks(
    briefing: CausalBriefing,
    portfolio: PortfolioAnalysis,
) -> dict[str, bool]:
    """
    Runs all rule-based checks and returns a name → pass/fail mapping.

    Failures are silently recorded rather than raised so the evaluator can
    report a partial score even when some checks fail.
    """
    return {
        name: check_fn(briefing, portfolio)[0]
        for name, check_fn in _RULE_FUNCTIONS.items()
    }
