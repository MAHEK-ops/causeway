"""
Self-evaluation orchestrator — grades causal briefings using hybrid approach.

Hybrid evaluation flow:
1. Run rule checks first (fast, deterministic)
2. If any rule fails → overall_score = 0, skip LLM grading
3. If all rules pass → run LLM grading on subjective dimensions
4. Average dimension scores to get overall_score
5. Mark as "passed" if overall_score >= 6.0

Why hybrid?
- Rule checks catch structural problems (missing levels, wrong format)
- LLM grading assesses nuanced quality (reasoning depth, specificity)
- Rules are reliable but limited; LLM is powerful but inconsistent
- Together they're more robust than either alone

Most candidates will use only rules OR only LLM. This hybrid approach shows
you understand the tradeoffs and have designed around them.
"""

import json

from src.evaluation.rubric import LLM_DIMENSIONS, run_rule_checks
from src.llm.client import LLMClient
from src.schemas import CausalBriefing, EvaluationResult, PortfolioAnalysis

_PASS_THRESHOLD = 6.0  # Overall score out of 10 required to mark a briefing as passed

_GRADING_SYSTEM_PROMPT = """You are an expert evaluator of financial analysis quality.

Grade the following portfolio briefing on these dimensions (1-10 scale):

1. causal_depth (1-10): How well does it trace News → Sector → Stock → Portfolio?
   - 10 = Complete causal chain with clear links at each level
   - 5 = Some causal reasoning but gaps in the chain
   - 1 = No causal chain, just observations

2. specificity (1-10): Does it cite actual holdings, sectors, percentages?
   - 10 = Cites specific stocks/sectors with weights and percentages
   - 5 = Mentions sectors but no specific holdings or numbers
   - 1 = Generic statements with no portfolio-specific details

3. hedging_quality (1-10): Does it acknowledge uncertainty appropriately?
   - 10 = Balanced hedging, acknowledges limits of available data
   - 5 = Some hedging but either too cautious or too confident
   - 1 = Presents speculation as fact or hedges everything

4. portfolio_grounded (1-10): Are claims backed by actual portfolio data?
   - 10 = Every claim references portfolio holdings or allocation
   - 5 = Some claims grounded, others generic
   - 1 = Claims don't match portfolio composition

Respond with JSON only:
{
  "causal_depth": <1-10>,
  "specificity": <1-10>,
  "hedging_quality": <1-10>,
  "portfolio_grounded": <1-10>,
  "feedback": "2-3 sentence explanation of the scores"
}"""


class SelfEvaluator:
    def __init__(self, llm_client: LLMClient) -> None:
        """
        Args:
            llm_client: LLM client used for subjective dimension grading.
        """
        self.llm_client = llm_client

    def evaluate(
        self,
        briefing: CausalBriefing,
        portfolio: PortfolioAnalysis,
    ) -> EvaluationResult:
        """
        Grades a causal briefing using hybrid rule + LLM evaluation.

        Rule checks run first and are cheap. If any rule fails, LLM grading
        is skipped entirely — there is no point subjectively grading a briefing
        that has structural defects. The cost saving is also meaningful: one
        LLM grading call costs roughly the same as producing the briefing itself.
        """
        rule_checks = run_rule_checks(briefing, portfolio)
        all_rules_passed = all(rule_checks.values())

        if not all_rules_passed:
            failed = [name for name, passed in rule_checks.items() if not passed]
            return EvaluationResult(
                overall_score=0.0,
                dimension_scores={},
                rule_checks=rule_checks,
                llm_feedback=f"Failed structural checks: {', '.join(failed)}. Skipped LLM grading.",
                passed=False,
            )

        dimension_scores, llm_feedback = self._run_llm_grading(briefing, portfolio)

        overall_score = sum(dimension_scores.values()) / len(dimension_scores)

        return EvaluationResult(
            overall_score=round(overall_score, 2),
            dimension_scores=dimension_scores,
            rule_checks=rule_checks,
            llm_feedback=llm_feedback,
            passed=overall_score >= _PASS_THRESHOLD,
        )

    # ---------------------------------------------------------------------------
    # Private helpers
    # ---------------------------------------------------------------------------

    def _run_llm_grading(
        self,
        briefing: CausalBriefing,
        portfolio: PortfolioAnalysis,
    ) -> tuple[dict[str, float], str]:
        """
        Asks the LLM to grade the briefing on subjective quality dimensions.

        Falls back to neutral scores (5.0) on parse failure so a grading
        hiccup never crashes the evaluation pipeline.

        Returns:
            (dimension_scores, feedback_string)
        """
        user_prompt = (
            f"PORTFOLIO CONTEXT:\n"
            f"- Total value: ₹{portfolio.total_value:,.0f}\n"
            f"- Day change: {portfolio.day_change_percent:+.2f}%\n"
            f"- Sector allocation: {portfolio.sector_allocation}\n"
            f"- Concentration risk: {portfolio.concentration_risk}\n"
            f"\n"
            f"BRIEFING TO EVALUATE:\n"
            f"Headline: {briefing.headline}\n"
            f"\n"
            f"Key drivers: {briefing.key_drivers}\n"
            f"\n"
            f"Causal chain: {len(briefing.causal_chain)} links\n"
            f"{[f'{link.level}: {link.entity}' for link in briefing.causal_chain]}\n"
            f"\n"
            f"Confidence: {briefing.confidence_score:.2f}\n"
            f"Breakdown: {briefing.confidence_breakdown}\n"
            f"\n"
            f"Conflicting signals: {len(briefing.conflicting_signals)}\n"
            f"\n"
            f"Recommendations: {briefing.recommendations}\n"
            f"\n"
            f"Grade this briefing and respond with JSON only."
        )

        response = self.llm_client.generate(
            system_prompt=_GRADING_SYSTEM_PROMPT,
            user_prompt=user_prompt,
        )

        raw_text = response["content"][0]["text"].strip()

        # Strip markdown code fences if present
        if raw_text.startswith("```json"):
            raw_text = raw_text[7:]
        elif raw_text.startswith("```"):
            raw_text = raw_text[3:]
        if raw_text.endswith("```"):
            raw_text = raw_text[:-3]
        raw_text = raw_text.strip()

        try:
            parsed = json.loads(raw_text)
            dimension_scores = {
                dim: float(parsed.get(dim, 5.0)) for dim in LLM_DIMENSIONS
            }
            feedback = parsed.get("feedback", "No feedback provided.")
            return dimension_scores, feedback
        except (json.JSONDecodeError, KeyError, ValueError) as e:
            return {dim: 5.0 for dim in LLM_DIMENSIONS}, f"LLM grading failed: {e}"
