"""
Computes portfolio P&L, sector allocation, and concentration risk.

This is the second stage of the Portfolio Layer. It receives enriched portfolio
data (with current market prices merged in) and produces a complete PortfolioAnalysis
object that the reasoning layer will use to explain portfolio movements.
"""

from src.config import CONCENTRATION_RISK_THRESHOLD
from src.schemas import MutualFundHolding, PortfolioAnalysis, StockHolding


# MF categories that map to a specific sector; everything else is DIVERSIFIED_MF.
_SECTORAL_MF_MAP: dict[str, str] = {
    "SECTORAL_BANKING": "BANKING",
    "SECTORAL_IT": "INFORMATION_TECHNOLOGY",
}


def _mf_sector(category: str) -> str:
    return _SECTORAL_MF_MAP.get(category, "DIVERSIFIED_MF")


class PortfolioAnalyzer:
    def analyze(self, enriched_portfolio: dict) -> PortfolioAnalysis:
        """
        Computes all portfolio analytics from enriched holdings.

        Logic:
        1. Recompute investment_value and current_value from first principles
           (avoids stale pre-computed values in the raw data)
        2. Sum across all holdings to get total_value
        3. Derive per-holding day_change and weight_in_portfolio using total_value
        4. Aggregate weights by sector to build sector_allocation
        5. Flag concentration_risk if any sector exceeds CONCENTRATION_RISK_THRESHOLD
        6. Pick top gainer and top loser by day_change_percent
        """
        raw_stocks = enriched_portfolio.get("enriched_stocks", [])
        raw_mfs = enriched_portfolio.get("enriched_mutual_funds", [])

        # Step 1: compute per-holding values (without weight yet) 

        stock_calcs: list[dict] = []
        for s in raw_stocks:
            inv = s["quantity"] * s["avg_buy_price"]
            cur = s["quantity"] * s["current_price"]
            gl = cur - inv
            stock_calcs.append(
                {
                    "symbol": s["symbol"],
                    "name": s["name"],
                    "sector": s["sector"],
                    "quantity": s["quantity"],
                    "avg_buy_price": s["avg_buy_price"],
                    "current_price": s["current_price"],
                    "investment_value": round(inv, 2),
                    "current_value": round(cur, 2),
                    "gain_loss": round(gl, 2),
                    "gain_loss_percent": round(gl / inv * 100, 2) if inv else 0.0,
                    "day_change_percent": s["day_change_percent"],
                }
            )

        mf_calcs: list[dict] = []
        for m in raw_mfs:
            inv = m["units"] * m["avg_nav"]
            cur = m["units"] * m["current_nav"]
            gl = cur - inv
            mf_calcs.append(
                {
                    "scheme_code": m["scheme_code"],
                    "scheme_name": m["scheme_name"],
                    "category": m["category"],
                    "units": m["units"],
                    "avg_nav": m["avg_nav"],
                    "current_nav": m["current_nav"],
                    "investment_value": round(inv, 2),
                    "current_value": round(cur, 2),
                    "gain_loss": round(gl, 2),
                    "gain_loss_percent": round(gl / inv * 100, 2) if inv else 0.0,
                    "day_change_percent": m["day_change_percent"],
                }
            )

        # Step 2: total portfolio value 

        total_value = sum(s["current_value"] for s in stock_calcs) + sum(
            m["current_value"] for m in mf_calcs
        )

        if total_value == 0:
            return PortfolioAnalysis(
                portfolio_id=enriched_portfolio["portfolio_id"],
                user_name=enriched_portfolio["user_name"],
                portfolio_type=enriched_portfolio["portfolio_type"],
                total_value=0.0,
                day_change_absolute=0.0,
                day_change_percent=0.0,
            )

        # Step 3: build typed holding objects with weight and day_change

        stock_holdings: list[StockHolding] = []
        for s in stock_calcs:
            day_change = round(s["day_change_percent"] * s["current_value"] / 100, 2)
            weight = round(s["current_value"] / total_value, 4)
            stock_holdings.append(
                StockHolding(
                    symbol=s["symbol"],
                    name=s["name"],
                    sector=s["sector"],
                    quantity=s["quantity"],
                    avg_buy_price=s["avg_buy_price"],
                    current_price=s["current_price"],
                    investment_value=s["investment_value"],
                    current_value=s["current_value"],
                    gain_loss=s["gain_loss"],
                    gain_loss_percent=s["gain_loss_percent"],
                    day_change=day_change,
                    day_change_percent=s["day_change_percent"],
                    weight_in_portfolio=weight,
                )
            )

        mf_holdings: list[MutualFundHolding] = []
        for m in mf_calcs:
            day_change = round(m["day_change_percent"] * m["current_value"] / 100, 2)
            weight = round(m["current_value"] / total_value, 4)
            mf_holdings.append(
                MutualFundHolding(
                    scheme_code=m["scheme_code"],
                    scheme_name=m["scheme_name"],
                    category=m["category"],
                    units=m["units"],
                    avg_nav=m["avg_nav"],
                    current_nav=m["current_nav"],
                    investment_value=m["investment_value"],
                    current_value=m["current_value"],
                    gain_loss=m["gain_loss"],
                    gain_loss_percent=m["gain_loss_percent"],
                    day_change=day_change,
                    day_change_percent=m["day_change_percent"],
                    weight_in_portfolio=weight,
                )
            )

        # Step 4: portfolio-level totals 

        day_change_absolute = round(
            sum(h.day_change for h in stock_holdings)
            + sum(h.day_change for h in mf_holdings),
            2,
        )
        day_change_percent = round(day_change_absolute / total_value * 100, 2)

        # Step 5: sector allocation (fraction of total_value)

        sector_values: dict[str, float] = {}
        for h in stock_holdings:
            sector_values[h.sector] = sector_values.get(h.sector, 0.0) + h.current_value
        for h in mf_holdings:
            sector_key = _mf_sector(h.category)
            sector_values[sector_key] = sector_values.get(sector_key, 0.0) + h.current_value

        sector_allocation = {
            sector: round(val / total_value, 4) for sector, val in sector_values.items()
        }

        # Step 6: concentration risk 

        breached = [s for s, w in sector_allocation.items() if w > CONCENTRATION_RISK_THRESHOLD]
        concentration_risk = bool(breached)
        concentration_details = (
            f"High concentration: {', '.join(breached)} exceed {int(CONCENTRATION_RISK_THRESHOLD * 100)}% threshold"
            if concentration_risk
            else None
        )

        # Step 7: top gainer / loser across all holdings 

        all_summaries = [
            {"name": h.symbol, "type": "stock", "day_change_percent": h.day_change_percent}
            for h in stock_holdings
        ] + [
            {"name": h.scheme_name, "type": "mutual_fund", "day_change_percent": h.day_change_percent}
            for h in mf_holdings
        ]

        top_gainer = (
            max(all_summaries, key=lambda x: x["day_change_percent"]) if all_summaries else None
        )
        top_loser = (
            min(all_summaries, key=lambda x: x["day_change_percent"]) if all_summaries else None
        )

        return PortfolioAnalysis(
            portfolio_id=enriched_portfolio["portfolio_id"],
            user_name=enriched_portfolio["user_name"],
            portfolio_type=enriched_portfolio["portfolio_type"],
            total_value=round(total_value, 2),
            day_change_absolute=day_change_absolute,
            day_change_percent=day_change_percent,
            stocks=stock_holdings,
            mutual_funds=mf_holdings,
            sector_allocation=sector_allocation,
            concentration_risk=concentration_risk,
            concentration_details=concentration_details,
            top_gainer=top_gainer,
            top_loser=top_loser,
        )
