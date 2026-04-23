"""
Single source of truth for all constants used across Causeway.

No magic numbers should appear in logic modules — import from here instead.
"""

import os
from pathlib import Path

# ---------------------------------------------------------------------------
# PATHS
# ---------------------------------------------------------------------------

DATA_DIR = Path("data")
OUTPUTS_DIR = Path("outputs")
TRACES_DIR = Path("traces")

# Individual data files
MARKET_DATA_FILE = DATA_DIR / "market_data.json"
NEWS_DATA_FILE = DATA_DIR / "news_data.json"
PORTFOLIOS_FILE = DATA_DIR / "portfolios.json"
MUTUAL_FUNDS_FILE = DATA_DIR / "mutual_funds.json"
SECTOR_MAPPING_FILE = DATA_DIR / "sector_mapping.json"
HISTORICAL_DATA_FILE = DATA_DIR / "historical_data.json"

# ---------------------------------------------------------------------------
# LLM CONFIG
# ---------------------------------------------------------------------------

MODEL_NAME = "gemini-2.5-flash"
TEMPERATURE = 0.7
MAX_TOKENS = 4000
TIMEOUT_SECONDS = 60

# ---------------------------------------------------------------------------
# THRESHOLDS — drive rule-based business logic
# ---------------------------------------------------------------------------

# 40% portfolio weight in one sector triggers concentration risk alert
CONCENTRATION_RISK_THRESHOLD = 0.40

# Sentiment score magnitude above this is considered high-impact news
HIGH_IMPACT_NEWS_THRESHOLD = 0.60

# Holdings below 2% portfolio weight are excluded from news relevance scoring
RELEVANCE_MIN_WEIGHT = 0.02

# Briefings with overall confidence below this get a low-confidence flag
MIN_CONFIDENCE_SCORE = 0.3

# ---------------------------------------------------------------------------
# MARKET SENTIMENT THRESHOLDS
# ---------------------------------------------------------------------------

# Index day-change % (positive) that classifies as BULLISH
BULLISH_THRESHOLD = 0.5

# Index day-change % (negative) that classifies as BEARISH
BEARISH_THRESHOLD = -0.5

# ---------------------------------------------------------------------------
# CACHE CONFIG
# ---------------------------------------------------------------------------

CACHE_DIR = Path(".cache")
CACHE_ENABLED = True

# ---------------------------------------------------------------------------
# LANGFUSE CONFIG — observability backend (optional, falls back to JSONL)
# ---------------------------------------------------------------------------

LANGFUSE_PUBLIC_KEY: str | None = os.getenv("LANGFUSE_PUBLIC_KEY")
LANGFUSE_SECRET_KEY: str | None = os.getenv("LANGFUSE_SECRET_KEY")
LANGFUSE_HOST: str = os.getenv("LANGFUSE_HOST", "https://cloud.langfuse.com")
