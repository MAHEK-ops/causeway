#!/usr/bin/env python3
"""
Causeway CLI — Autonomous financial advisor agent

Orchestrates the full pipeline:
1. Load market data, news, portfolios
2. Run market intelligence analysis
3. Analyze portfolio holdings
4. Filter relevant news
5. Build reasoning context
6. Generate causal briefing with LLM
7. Self-evaluate the briefing
8. Write outputs (JSON + Markdown)

Usage:
    python run.py --portfolio PORTFOLIO_001
    python run.py --portfolio PORTFOLIO_002 --no-cache
    python run.py --all  # Run all portfolios
"""

import argparse
import json
import sys
from pathlib import Path

from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn

from dotenv import load_dotenv
load_dotenv()

sys.path.insert(0, str(Path(__file__).parent))

from src.config import (
    CACHE_DIR,
    CACHE_ENABLED,
    MARKET_DATA_FILE,
    MUTUAL_FUNDS_FILE,
    NEWS_DATA_FILE,
    PORTFOLIOS_FILE,
    SECTOR_MAPPING_FILE,
)
from src.evaluation.self_evaluator import SelfEvaluator
from src.llm.cache import LLMCache
from src.llm.client import LLMClient
from src.market_intel.market_analyzer import MarketAnalyzer
from src.market_intel.news_processor import NewsProcessor
from src.market_intel.sector_analyzer import SectorAnalyzer
from src.observability.logger import get_logger
from src.output.json_writer import JSONWriter
from src.output.markdown_renderer import MarkdownRenderer
from src.portfolio.analytics import PortfolioAnalyzer
from src.portfolio.enrichment import PortfolioEnricher
from src.reasoning.causal_agent import CausalAgent
from src.reasoning.context_builder import ContextBuilder
from src.reasoning.relevance_filter import RelevanceFilter

console = Console()
logger = get_logger(__name__)


def load_json(filepath: Path) -> dict | list:
    """Load JSON data from file with a clear error on missing files."""
    if not filepath.exists():
        console.print(f"[red]Data file not found: {filepath}[/red]")
        sys.exit(1)
    with open(filepath, encoding="utf-8") as f:
        return json.load(f)


def run_pipeline(portfolio_id: str, use_cache: bool = True) -> None:
    """
    Runs the full Causeway pipeline for a single portfolio.

    Args:
        portfolio_id: Portfolio ID to analyze (e.g. "PORTFOLIO_001")
        use_cache: Whether to use the LLM response disk cache
    """
    console.print(f"\n[bold cyan]Processing {portfolio_id}[/bold cyan]\n")

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:

        # ── Phase 1: Load Data ────────────────────────────────────────────
        task = progress.add_task("Loading data files...", total=None)

        market_data    = load_json(MARKET_DATA_FILE)
        news_raw       = load_json(NEWS_DATA_FILE)
        portfolios_raw = load_json(PORTFOLIOS_FILE)
        mutual_funds   = load_json(MUTUAL_FUNDS_FILE)
        sector_mapping = load_json(SECTOR_MAPPING_FILE)

        # portfolios.json stores portfolios as a dict keyed by portfolio_id
        portfolio_dict = portfolios_raw.get("portfolios", {})
        raw_portfolio  = portfolio_dict.get(portfolio_id)
        if raw_portfolio is None:
            console.print(f"[red]Portfolio '{portfolio_id}' not found. "
                          f"Available: {list(portfolio_dict.keys())}[/red]")
            return

        progress.update(task, description="✓ Data loaded")
        progress.remove_task(task)

        # ── Phase 2: Market Intelligence ──────────────────────────────────
        task = progress.add_task("Analyzing market conditions...", total=None)

        market_signal    = MarketAnalyzer().analyze(market_data["indices"])
        sector_trends    = SectorAnalyzer(sector_mapping).analyze(market_data["stocks"])
        classified_news  = NewsProcessor().process(news_raw["news"])

        progress.update(task, description="✓ Market intelligence complete")
        progress.remove_task(task)

        # ── Phase 3: Portfolio Analytics ─────────────────────────────────
        task = progress.add_task("Analyzing portfolio...", total=None)

        enriched        = PortfolioEnricher(market_data, sector_mapping, mutual_funds).enrich(
            portfolio_id, raw_portfolio
        )
        portfolio       = PortfolioAnalyzer().analyze(enriched)

        progress.update(task, description="✓ Portfolio analysis complete")
        progress.remove_task(task)

        # ── Phase 4: Reasoning ────────────────────────────────────────────
        task = progress.add_task("Filtering relevant news...", total=None)

        filtered_news = RelevanceFilter().filter(classified_news, portfolio)

        progress.update(task, description=f"✓ Filtered to {len(filtered_news)} relevant items")
        progress.remove_task(task)

        task = progress.add_task("Building reasoning context...", total=None)

        context = ContextBuilder().build(portfolio, filtered_news, market_signal, sector_trends)

        progress.update(task, description="✓ Context built")
        progress.remove_task(task)

        task = progress.add_task("Generating causal briefing (LLM)...", total=None)

        cache      = LLMCache(CACHE_DIR, enabled=use_cache and CACHE_ENABLED)
        llm_client = LLMClient(cache=cache)
        briefing   = CausalAgent(llm_client).analyze(context)

        progress.update(task, description="✓ Briefing generated")
        progress.remove_task(task)

        # ── Phase 5: Evaluation ───────────────────────────────────────────
        task = progress.add_task("Self-evaluating briefing...", total=None)

        evaluation = SelfEvaluator(llm_client).evaluate(briefing, portfolio)

        progress.update(
            task,
            description=f"✓ Evaluation complete (score: {evaluation.overall_score:.1f}/10)",
        )
        progress.remove_task(task)

        # ── Phase 6: Output ───────────────────────────────────────────────
        task = progress.add_task("Writing outputs...", total=None)

        json_path = JSONWriter().write(briefing, portfolio_id)
        md_path   = MarkdownRenderer().render(briefing, portfolio_id)

        progress.update(task, description="✓ Outputs written")
        progress.remove_task(task)

    # ── Summary ───────────────────────────────────────────────────────────
    console.print("\n[bold green]✓ Pipeline complete![/bold green]\n")
    console.print(f"  Headline:   {briefing.headline}")
    console.print(f"  Confidence: {briefing.confidence_score:.0%}")
    console.print(
        f"  Evaluation: {evaluation.overall_score:.1f}/10 "
        f"({'[green]PASS[/green]' if evaluation.passed else '[red]FAIL[/red]'})"
    )
    console.print(f"\n  JSON:     {json_path}")
    console.print(f"  Markdown: {md_path}\n")

    logger.info(
        "Pipeline completed",
        portfolio_id=portfolio_id,
        confidence=briefing.confidence_score,
        evaluation_score=evaluation.overall_score,
        passed=evaluation.passed,
    )


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Causeway — Autonomous Financial Advisor",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "--portfolio",
        type=str,
        metavar="ID",
        help="Portfolio ID to analyze (e.g. PORTFOLIO_001)",
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="Run pipeline for all portfolios in data/portfolios.json",
    )
    parser.add_argument(
        "--no-cache",
        action="store_true",
        help="Disable LLM response caching",
    )

    args = parser.parse_args()
    use_cache = not args.no_cache

    if args.all:
        portfolio_dict = load_json(PORTFOLIOS_FILE).get("portfolios", {})
        ids = list(portfolio_dict.keys())
        console.print(f"\n[bold]Running pipeline for {len(ids)} portfolios[/bold]")
        for pid in ids:
            run_pipeline(pid, use_cache=use_cache)

    elif args.portfolio:
        run_pipeline(args.portfolio, use_cache=use_cache)

    else:
        console.print("[red]Error: specify --portfolio ID or --all[/red]\n")
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
