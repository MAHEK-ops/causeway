"""
Unit tests for PortfolioAnalyzer — verifying P&L calculations are mathematically correct.

These tests use simple, hand-verifiable numbers to ensure the portfolio analytics
produce accurate results. The math here is critical — it's the ground truth the
LLM will cite when explaining portfolio movements.
"""

import pytest

from src.config import CONCENTRATION_RISK_THRESHOLD
from src.portfolio.analytics import PortfolioAnalyzer

# Helpers

def _stock(
    symbol: str = "S1",
    sector: str = "BANKING",
    quantity: int = 100,
    avg_buy_price: float = 10.0,
    current_price: float = 12.0,
    day_change_percent: float = 2.0,
) -> dict:
    return {
        "symbol": symbol,
        "name": symbol,
        "sector": sector,
        "quantity": quantity,
        "avg_buy_price": avg_buy_price,
        "current_price": current_price,
        "day_change_percent": day_change_percent,
    }


def _mf(
    scheme_code: str = "MF1",
    scheme_name: str = "Test Fund",
    category: str = "FLEXI_CAP",
    units: float = 50.0,
    avg_nav: float = 100.0,
    current_nav: float = 110.0,
    day_change_percent: float = -1.0,
) -> dict:
    return {
        "scheme_code": scheme_code,
        "scheme_name": scheme_name,
        "category": category,
        "units": units,
        "avg_nav": avg_nav,
        "current_nav": current_nav,
        "day_change_percent": day_change_percent,
    }


def _portfolio(stocks: list[dict] | None = None, mfs: list[dict] | None = None) -> dict:
    return {
        "portfolio_id": "TEST_001",
        "user_name": "Test User",
        "portfolio_type": "TEST",
        "enriched_stocks": stocks or [],
        "enriched_mutual_funds": mfs or [],
    }

# Tests

def test_stock_pnl_calculation():
    """100 shares bought at 10, now at 12 — verify investment, current value, and gain/loss."""
    result = PortfolioAnalyzer().analyze(
        _portfolio(stocks=[_stock(quantity=100, avg_buy_price=10.0, current_price=12.0, day_change_percent=2.0)])
    )

    s = result.stocks[0]
    assert s.investment_value == 1000.0      # 100 × 10
    assert s.current_value == 1200.0         # 100 × 12
    assert s.gain_loss == 200.0              # 1200 - 1000
    assert s.gain_loss_percent == 20.0       # 200/1000 × 100
    assert s.day_change == 24.0              # 2% of 1200


def test_mutual_fund_pnl_calculation():
    """50 units at NAV 100, now at 110 — verify investment, current value, and gain/loss."""
    result = PortfolioAnalyzer().analyze(
        _portfolio(mfs=[_mf(units=50.0, avg_nav=100.0, current_nav=110.0, day_change_percent=-1.0)])
    )

    m = result.mutual_funds[0]
    assert m.investment_value == 5000.0      # 50 × 100
    assert m.current_value == 5500.0         # 50 × 110
    assert m.gain_loss == 500.0              # 5500 - 5000
    assert m.gain_loss_percent == 10.0       # 500/5000 × 100
    assert m.day_change == -55.0             # -1% of 5500


def test_day_change_calculation():
    """day_change must equal day_change_percent × current_value / 100."""
    result = PortfolioAnalyzer().analyze(
        _portfolio(stocks=[_stock(quantity=10, avg_buy_price=100.0, current_price=100.0, day_change_percent=-2.0)])
    )

    s = result.stocks[0]
    assert s.current_value == 1000.0
    assert s.day_change == -20.0             # -2% of 1000


def test_portfolio_totals():
    """Two stocks with opposite moves — verify totals are summed correctly."""
    # stock1: cv=1000, day_change=-2% → dc=-20
    # stock2: cv=500,  day_change=+2% → dc=+10
    enriched = _portfolio(
        stocks=[
            _stock("S1", quantity=10, avg_buy_price=100.0, current_price=100.0, day_change_percent=-2.0),
            _stock("S2", quantity=5,  avg_buy_price=100.0, current_price=100.0, day_change_percent=2.0),
        ]
    )

    result = PortfolioAnalyzer().analyze(enriched)

    assert result.total_value == 1500.0
    assert result.day_change_absolute == -10.0    # -20 + 10
    assert result.day_change_percent == -0.67     # -10/1500 × 100, rounded to 2dp


def test_sector_allocation():
    """Two stocks in different sectors — weights should reflect their share of total value."""
    # BANKING cv=600, IT cv=400, total=1000
    enriched = _portfolio(
        stocks=[
            _stock("S1", sector="BANKING",               quantity=6,  avg_buy_price=100.0, current_price=100.0),
            _stock("S2", sector="INFORMATION_TECHNOLOGY", quantity=4, avg_buy_price=100.0, current_price=100.0),
        ]
    )

    result = PortfolioAnalyzer().analyze(enriched)

    assert result.sector_allocation["BANKING"] == 0.6
    assert result.sector_allocation["INFORMATION_TECHNOLOGY"] == 0.4
    assert abs(sum(result.sector_allocation.values()) - 1.0) < 1e-9


def test_concentration_risk_triggered():
    """A sector exceeding the 40% threshold should set concentration_risk=True."""
    # BANKING covers 60% of the portfolio
    enriched = _portfolio(
        stocks=[
            _stock("S1", sector="BANKING",               quantity=6, avg_buy_price=100.0, current_price=100.0),
            _stock("S2", sector="INFORMATION_TECHNOLOGY", quantity=4, avg_buy_price=100.0, current_price=100.0),
        ]
    )

    result = PortfolioAnalyzer().analyze(enriched)

    assert result.concentration_risk is True
    assert result.concentration_details is not None
    assert "BANKING" in result.concentration_details


def test_concentration_risk_not_triggered():
    """No sector exceeding the threshold — concentration_risk must be False."""
    # Three sectors at 40% / 40% / 20% — exactly at threshold is NOT a breach (strict >)
    enriched = _portfolio(
        stocks=[
            _stock("S1", sector="BANKING",               quantity=4, avg_buy_price=100.0, current_price=100.0),
            _stock("S2", sector="INFORMATION_TECHNOLOGY", quantity=4, avg_buy_price=100.0, current_price=100.0),
            _stock("S3", sector="FMCG",                  quantity=2, avg_buy_price=100.0, current_price=100.0),
        ]
    )

    result = PortfolioAnalyzer().analyze(enriched)

    assert result.concentration_risk is False
    assert result.concentration_details is None


def test_top_gainer_and_loser():
    """top_gainer and top_loser must reflect the extreme day_change_percent holdings."""
    enriched = _portfolio(
        stocks=[
            _stock("WINNER", quantity=1, avg_buy_price=100.0, current_price=100.0, day_change_percent=5.0),
            _stock("LOSER",  quantity=1, avg_buy_price=100.0, current_price=100.0, day_change_percent=-3.0),
        ]
    )

    result = PortfolioAnalyzer().analyze(enriched)

    assert result.top_gainer is not None
    assert result.top_loser is not None
    assert result.top_gainer["day_change_percent"] == 5.0
    assert result.top_loser["day_change_percent"] == -3.0


def test_empty_portfolio():
    """An empty portfolio must return zeros without raising any exception."""
    result = PortfolioAnalyzer().analyze(_portfolio())

    assert result.total_value == 0.0
    assert result.day_change_absolute == 0.0
    assert result.day_change_percent == 0.0
    assert result.stocks == []
    assert result.mutual_funds == []


def test_mutual_fund_sector_mapping():
    """SECTORAL_BANKING MF maps to BANKING; non-sectoral MF maps to DIVERSIFIED_MF."""
    enriched = _portfolio(
        mfs=[
            _mf("MF_BANK",  category="SECTORAL_BANKING", units=1, avg_nav=100.0, current_nav=100.0),
            _mf("MF_FLEX",  category="FLEXI_CAP",        units=1, avg_nav=100.0, current_nav=100.0),
            _mf("MF_LARGE", category="LARGE_CAP",        units=1, avg_nav=100.0, current_nav=100.0),
        ]
    )

    result = PortfolioAnalyzer().analyze(enriched)

    assert "BANKING" in result.sector_allocation
    assert "DIVERSIFIED_MF" in result.sector_allocation
    # SECTORAL_IT mapping check via a second pass
    enriched_it = _portfolio(mfs=[_mf("MF_IT", category="SECTORAL_IT", units=1, avg_nav=100.0, current_nav=100.0)])
    result_it = PortfolioAnalyzer().analyze(enriched_it)
    assert "INFORMATION_TECHNOLOGY" in result_it.sector_allocation
