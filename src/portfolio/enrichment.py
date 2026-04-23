"""
Joins portfolio holdings with live market data and sector mappings.

This is the first stage of the Portfolio Layer. It takes raw portfolio data
and merges in current prices, day changes, and sector classifications so that
downstream analytics can compute accurate P&L and allocations.
"""


class PortfolioEnricher:
    def __init__(
        self,
        market_data: dict,
        sector_mapping: dict,
        mutual_funds_data: dict,
    ) -> None:
        """
        Args:
            market_data: Parsed market_data.json
            sector_mapping: Parsed sector_mapping.json
            mutual_funds_data: Parsed mutual_funds.json
        """
        self._stocks: dict[str, dict] = market_data.get("stocks", {})
        self._sector_for_stock: dict[str, str] = {
            symbol: sector_name
            for sector_name, info in sector_mapping.get("sectors", {}).items()
            for symbol in info.get("stocks", [])
        }
        self._mf_data: dict[str, dict] = mutual_funds_data.get("mutual_funds", {})

    def enrich(self, portfolio_id: str, raw_portfolio: dict) -> dict:
        """
        Merges a raw portfolio with authoritative live market prices.

        The raw portfolio may carry stale current_price / current_nav values from
        when it was exported. This method overwrites them with live data so that
        analytics.py always works from correct prices.

        Returns a flat dict with:
          - portfolio_id, user_name, portfolio_type (metadata passthrough)
          - enriched_stocks: list of merged stock dicts (raw fields + live price/change)
          - enriched_mutual_funds: list of merged MF dicts (raw fields + live NAV/change)
        """
        enriched_stocks: list[dict] = []
        for holding in raw_portfolio["holdings"].get("stocks", []):
            symbol = holding["symbol"]
            if symbol not in self._stocks:
                raise ValueError(
                    f"Stock '{symbol}' not found in market data — "
                    "cannot compute accurate current value"
                )
            live = self._stocks[symbol]

            # Prefer sector_mapping as the authoritative sector source;
            # fall back to what the portfolio file says.
            sector = self._sector_for_stock.get(symbol, holding.get("sector", "UNKNOWN"))

            enriched_stocks.append(
                {
                    **holding,
                    "sector": sector,
                    "name": live.get("name", holding.get("name", symbol)),
                    # Overwrite with authoritative live values
                    "current_price": live["current_price"],
                    "day_change_percent": live["change_percent"],
                }
            )

        enriched_mfs: list[dict] = []
        for holding in raw_portfolio["holdings"].get("mutual_funds", []):
            scheme_code = holding["scheme_code"]
            if scheme_code not in self._mf_data:
                raise ValueError(
                    f"Mutual fund '{scheme_code}' not found in mutual funds data — "
                    "cannot compute accurate current value"
                )
            live = self._mf_data[scheme_code]

            enriched_mfs.append(
                {
                    **holding,
                    "scheme_name": live.get("scheme_name", holding.get("scheme_name", scheme_code)),
                    "category": live.get("category", holding.get("category", "UNKNOWN")),
                    # Overwrite with authoritative live values
                    "current_nav": live["current_nav"],
                    "day_change_percent": live["nav_change_percent"],
                }
            )

        return {
            "portfolio_id": portfolio_id,
            "user_name": raw_portfolio["user_name"],
            "portfolio_type": raw_portfolio["portfolio_type"],
            "enriched_stocks": enriched_stocks,
            "enriched_mutual_funds": enriched_mfs,
        }
