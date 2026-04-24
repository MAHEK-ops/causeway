# Causeway

> Autonomous financial advisor agent with causal reasoning. Explains portfolio movements through News → Sector → Stock → Portfolio chains.

Built for YC-backed startup Backend + AI Engineer Intern assignment (48-hour takehome).

---

## Quick Start

```bash
# Clone and setup
git clone https://github.com/MAHEK-ops/causeway.git
cd causeway
python3.11 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Configure API key
cp .env.example .env
# Add your GOOGLE_API_KEY to .env

# Run the agent
python run.py --portfolio PORTFOLIO_001

# Or try the interactive UI
streamlit run app.py
```

**Output:** JSON + Markdown briefings in `outputs/`

**Live Demo:** [causeway-vbx3rixeqtsshs6dndaqjs.streamlit.app](https://causeway-vbx3rixeqtsshs6dndaqjs.streamlit.app/)

---

## What Makes This Different

Most candidates will dump all data into an LLM and ask "what happened?"

Causeway uses a multi-stage reasoning pipeline with pre-filtering and structured prompts:

1. **Pre-LLM relevance filter** - Ticker-based news filtering cuts tokens by ~75%
2. **Minimal context builder** - Sends ~800 tokens vs ~3000 (token diet)
3. **Versioned prompts** - Treated as code with ADR-style documentation
4. **4D confidence breakdown** - Interpretable scoring (data coverage, signal agreement, chain completeness, concentration)
5. **Hybrid evaluation** - Rules check structure, LLM grades quality
6. **Structured output with auto-retry** - LLM self-corrects on validation failure
7. **No frameworks** - Built from scratch for full transparency (no LangChain, no agent libraries)

**Token efficiency:** ~1200 tokens per briefing vs ~4000 without filtering  
**Quality:** 9+ evaluation scores across all 3 test portfolios  
**Architecture:** Zero dependencies on agent frameworks - every abstraction is explained

---

## How It Works

1. **Load** market data, news, portfolio holdings
2. **Analyze** market sentiment and sector trends  
3. **Filter** news by matching against portfolio tickers (~75% token reduction)
4. **Build** minimal context (~800 tokens vs ~3000)
5. **Generate** causal briefing via LLM with structured output
6. **Evaluate** using hybrid rules + LLM grading
7. **Output** JSON (machine-readable) + Markdown (human-readable)

**End-to-end latency:** ~10-15 seconds per portfolio

---

## Architecture

**Project Structure:**
```
causeway/
├── src/
│   ├── config.py              # Configuration management
│   ├── schemas.py             # Pydantic data models
│   │
│   ├── market_intel/          # Market context analysis
│   │   ├── market_analyzer.py
│   │   ├── sector_analyzer.py
│   │   └── news_processor.py
│   │
│   ├── portfolio/             # Portfolio analytics
│   │   ├── enrichment.py
│   │   └── analytics.py
│   │
│   ├── llm/                   # LLM infrastructure
│   │   ├── cache.py
│   │   └── client.py
│   │
│   ├── reasoning/             # Causal reasoning agent
│   │   ├── relevance_filter.py
│   │   ├── context_builder.py
│   │   ├── prompts.py
│   │   └── causal_agent.py
│   │
│   ├── evaluation/            # Self-evaluation system
│   │   ├── rubric.py
│   │   └── self_evaluator.py
│   │
│   ├── observability/         # Tracing and logging
│   │   ├── tracer.py
│   │   └── logger.py
│   │
│   └── output/                # Output formatting
│       ├── json_writer.py
│       └── markdown_renderer.py
│
├── data/                      # Mock market data
├── outputs/                   # Generated briefings (3 samples)
├── app.py                     # Streamlit frontend
├── run.py                     # CLI entry point
└── tests/                     # Unit tests
```

**Pipeline Flow:**

1. **Market Intel** - Analyze indices, sectors, news sentiment
2. **Portfolio Analytics** - Calculate P&L, allocation, risk metrics
3. **Relevance Filter** - Match news against portfolio tickers (75% reduction)
4. **Context Builder** - Assemble minimal prompt (~800 tokens)
5. **Causal Agent** - Generate structured briefing via LLM with auto-retry
6. **Self-Evaluator** - Hybrid rules + LLM grading (9+ scores)
7. **Output** - JSON + Markdown files

**Observability:** Langfuse integration with JSONL fallback. When Langfuse credentials aren't configured, traces write to `traces/llm_traces.jsonl`.

---

## Interactive UI

Features:
- Compare all 3 test portfolios side-by-side
- Interactive confidence breakdown with visual progress bars
- 4 tabs: Key Drivers, Causal Chain, Conflicting Signals, Recommendations
- Color-coded causal levels (News → Sector → Stock → Portfolio)
- Dark theme with professional styling

Run locally:
```bash
streamlit run app.py
```

---

## Design Decisions

**Why Gemini over Claude?** Free tier (no cost for takehome). Architecture is model-agnostic with clean abstraction layer.

**Why hand-rolled agent over LangChain?** JD values "knowing why things work or break" — frameworks hide implementation details. Building from scratch means every decision is documented and transparent.

**Why hybrid evaluation?** Rules catch structural problems (missing levels, wrong format, invalid stock references). LLM grades subjective quality (reasoning depth, specificity, actionability). Together they're more robust than either alone.

**Why pre-filter news?** Most candidates send all 25 headlines to the LLM. Pre-filtering by matching tickers drops irrelevant news before the LLM call, cutting tokens by 75% and keeping the analysis focused.

**Why Streamlit?** Demonstrates end-to-end product thinking. The UI lets non-technical users explore causal chains interactively without running Python scripts.

---

## Testing

```bash
# Run unit tests
pytest tests/

# Run all portfolios
python run.py --all

# Disable cache (force fresh LLM calls)
python run.py --portfolio PORTFOLIO_001 --no-cache

# Run with observability tracing
# Set LANGFUSE_PUBLIC_KEY and LANGFUSE_SECRET_KEY in .env
python run.py --portfolio PORTFOLIO_002
```

---

## Tech Stack

- **Python 3.11** (Pydantic 2.x compatibility)
- **Google Gemini 2.5 Flash** (free tier, fast, strong reasoning)
- **Pydantic** (type-safe schemas, automatic validation)
- **Streamlit** (interactive frontend)
- **Rich** (CLI progress bars and colored output)
- **Langfuse** (observability, with JSONL fallback)
- **DiskCache** (SHA256-based response caching)

**No agent frameworks** - built from scratch for full transparency and control.

---

## Results

All 3 test portfolios scored **9+ out of 10** on self-evaluation:

| Portfolio | Type | Confidence | Evaluation |
|-----------|------|------------|------------|
| PORTFOLIO_001 | Diversified (38% stocks, 62% MF) | 81% | 9.8/10 |
| PORTFOLIO_002 | Concentrated Banking (91% banking) | 90% | 9.5/10 |
| PORTFOLIO_003 | Conservative (21% stocks, 79% MF) | 84% | 9.2/10 |

**Confidence breakdown** is interpretable:
- **Data Coverage** (90-100%): Do we have complete market data?
- **Signal Agreement** (70-85%): Do news sentiment and price movements align?
- **Chain Completeness** (100%): Are all causal levels (news → sector → stock → portfolio) present?
- **Holding Concentration** (100%): Are cited stocks actually in the portfolio?

---

## Development Notes

**Token optimization:**
- Without filtering: ~4000 tokens per briefing
- With ticker-based filtering: ~1200 tokens per briefing
- Savings: 70% reduction in LLM costs

**Cache hit rate:**
- Development: ~80% (iterating on prompts)
- Production: Would vary by news freshness

**Observability:**
- Every LLM call is traced (prompt, response, tokens, duration)
- Langfuse for production, JSONL fallback for development
- Full conversation history preserved for debugging

---

## License

Built as a takehome assignment. Not for production use.
