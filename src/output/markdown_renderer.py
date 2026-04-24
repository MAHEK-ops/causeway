"""
Markdown rendering for causal briefings.

Why markdown output?
- Human-readable: Portfolio managers can read reports directly
- Formatted: Headers, lists, emphasis make structure clear
- Portable: Renders in GitHub, Notion, email, browsers
- Diffable: Git can show changes between briefings over time

The markdown files in outputs/ serve as:
1. Executive summaries for stakeholders
2. Reports for portfolio managers
3. Documentation of reasoning for compliance
4. Readable artifacts committed to git

Usage:
    renderer = MarkdownRenderer()
    filepath = renderer.render(briefing, portfolio_id="P001")
    print(f"Wrote briefing to {filepath}")
"""

from datetime import datetime
from pathlib import Path

from src.config import OUTPUTS_DIR
from src.schemas import CausalBriefing


class MarkdownRenderer:
    """
    Renders CausalBriefing objects as human-readable markdown reports.

    Output path pattern: outputs/{portfolio_id}_{timestamp}.md

    Usage:
        renderer = MarkdownRenderer()
        renderer.render(briefing, portfolio_id="PORTFOLIO_001")
        # Creates: outputs/PORTFOLIO_001_2026-04-23T10-30-00.md
    """

    def __init__(self, output_dir: Path = OUTPUTS_DIR) -> None:
        """
        Args:
            output_dir: Directory where markdown files will be written.
        """
        self.output_dir = output_dir
        self.output_dir.mkdir(exist_ok=True, parents=True)

    def render(self, briefing: CausalBriefing, portfolio_id: str) -> Path:
        """
        Renders a briefing as a formatted markdown document.

        Returns:
            Path to the written markdown file.
        """
        timestamp = datetime.utcnow().strftime("%Y-%m-%dT%H-%M-%S")
        filepath = self.output_dir / f"{portfolio_id}_{timestamp}.md"

        filepath.write_text(self._build_markdown(briefing, portfolio_id), encoding="utf-8")
        return filepath

    def _build_markdown(self, briefing: CausalBriefing, portfolio_id: str) -> str:
        """Assembles all sections into the final markdown string."""
        sections: list[str] = []

        # Header
        sections.append(f"# Portfolio Briefing: {portfolio_id}")
        sections.append(f"\n**Generated:** {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}")
        sections.append(f"\n**Confidence:** {briefing.confidence_score:.0%}\n")
        sections.append("---\n")

        # Headline
        sections.append(f"## {briefing.headline}\n")

        # Key Drivers 
        sections.append("## Key Drivers\n")
        for i, driver in enumerate(briefing.key_drivers, 1):
            sections.append(f"{i}. {driver}")
        sections.append("")

        # Causal Chain
        sections.append("## Causal Chain\n")
        for link in briefing.causal_chain:
            magnitude = f" ({link.magnitude:+.2f}%)" if link.magnitude is not None else ""
            sections.append(f"**{link.level}** → {link.entity}{magnitude}")
            sections.append(f"  - {link.impact}\n")

        # Conflicting Signals (optional section)
        if briefing.conflicting_signals:
            sections.append("## Conflicting Signals\n")
            for signal in briefing.conflicting_signals:
                sections.append(f"**{signal.entity}**")
                sections.append(f"  - News sentiment: {signal.news_sentiment}")
                sections.append(f"  - Price movement: {signal.price_movement}")
                sections.append(f"  - Explanation: {signal.explanation}\n")

        # Confidence Breakdown
        sections.append("## Confidence Breakdown\n")
        for dimension, score in briefing.confidence_breakdown.items():
            sections.append(f"- **{dimension.replace('_', ' ').title()}:** {score:.0%}")
        sections.append("")

        # Recommendations
        sections.append("## Recommendations\n")
        for i, rec in enumerate(briefing.recommendations, 1):
            sections.append(f"{i}. {rec}")
        sections.append("")

        return "\n".join(sections)
