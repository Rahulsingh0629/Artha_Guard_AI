class AssetAllocator:
    
    def get_suggested_allocation(self, risk_category: str) -> dict:
        """
        Returns the ideal portfolio split based on risk category.
        """
        if risk_category == "AGGRESSIVE":
            return {
                "Equity (Stocks)": "70%",
                "Mutual Funds": "15%",
                "Gold/Commodities": "10%",
                "Liquid Cash": "5%",
                "Strategy": "Focus on High Growth sectors (Tech, EV, Small Cap)."
            }
        elif risk_category == "MODERATE":
            return {
                "Equity (Stocks)": "50%",
                "Debt/Bonds": "30%",
                "Gold": "15%",
                "Liquid Cash": "5%",
                "Strategy": "Balance between stability (FMCG) and growth (Banking)."
            }
        else: # CONSERVATIVE
            return {
                "Fixed Deposits/Debt": "60%",
                "Index Funds (Nifty 50)": "20%",
                "Gold": "15%",
                "Cash": "5%",
                "Strategy": "Protect capital. Minimize volatility."
            }

    def get_stock_recommendations(self, risk_category: str) -> list:
        """
        Curated stock and ETF ideas by risk profile.
        These are educational suggestions, not guaranteed returns.
        """
        if risk_category == "AGGRESSIVE":
            return [
                {
                    "name": "NIFTYBEES (Nippon India ETF Nifty 50)",
                    "type": "ETF",
                    "allocation_hint": "35% of equity bucket",
                    "why": "Low-cost broad-market exposure to India's top companies.",
                    "expected_return_range_annual": "10% - 14%"
                },
                {
                    "name": "Tata Motors",
                    "type": "Stock",
                    "allocation_hint": "15% of equity bucket",
                    "why": "Auto + EV growth potential with global scale.",
                    "expected_return_range_annual": "12% - 18%"
                },
                {
                    "name": "Larsen & Toubro (L&T)",
                    "type": "Stock",
                    "allocation_hint": "15% of equity bucket",
                    "why": "Infrastructure capex beneficiary with diversified engineering exposure.",
                    "expected_return_range_annual": "11% - 16%"
                },
                {
                    "name": "HDFC Bank",
                    "type": "Stock",
                    "allocation_hint": "15% of equity bucket",
                    "why": "Large private bank with strong credit quality and retail franchise.",
                    "expected_return_range_annual": "10% - 15%"
                },
                {
                    "name": "Infosys",
                    "type": "Stock",
                    "allocation_hint": "20% of equity bucket",
                    "why": "High-quality IT exporter with strong cash flows.",
                    "expected_return_range_annual": "9% - 14%"
                },
            ]
        if risk_category == "MODERATE":
            return [
                {
                    "name": "NIFTYBEES (Nippon India ETF Nifty 50)",
                    "type": "ETF",
                    "allocation_hint": "45% of equity bucket",
                    "why": "Core diversified equity base with lower single-stock risk.",
                    "expected_return_range_annual": "10% - 13%"
                },
                {
                    "name": "ICICI Prudential Nifty Next 50 ETF",
                    "type": "ETF",
                    "allocation_hint": "20% of equity bucket",
                    "why": "Adds large-cap growth names beyond Nifty 50.",
                    "expected_return_range_annual": "11% - 15%"
                },
                {
                    "name": "HDFC Bank",
                    "type": "Stock",
                    "allocation_hint": "12% of equity bucket",
                    "why": "Stable earnings profile in private banking.",
                    "expected_return_range_annual": "10% - 14%"
                },
                {
                    "name": "ITC",
                    "type": "Stock",
                    "allocation_hint": "11% of equity bucket",
                    "why": "Defensive cash-generating FMCG + cigarette franchise.",
                    "expected_return_range_annual": "8% - 12%"
                },
                {
                    "name": "Infosys",
                    "type": "Stock",
                    "allocation_hint": "12% of equity bucket",
                    "why": "Quality technology export business with global client base.",
                    "expected_return_range_annual": "9% - 13%"
                },
            ]
        return [
            {
                "name": "NIFTYBEES (Nippon India ETF Nifty 50)",
                "type": "ETF",
                "allocation_hint": "55% of equity bucket",
                "why": "Broad-market diversification with lower management churn.",
                "expected_return_range_annual": "9% - 12%"
            },
            {
                "name": "SBI Magnum Gilt Fund",
                "type": "Debt Fund",
                "allocation_hint": "25% of total portfolio",
                "why": "Government bond exposure for capital preservation.",
                "expected_return_range_annual": "6% - 8%"
            },
            {
                "name": "HDFC Bank",
                "type": "Stock",
                "allocation_hint": "10% of equity bucket",
                "why": "Relatively stable large-cap private sector bank.",
                "expected_return_range_annual": "9% - 13%"
            },
            {
                "name": "Gold ETF (e.g., GOLDBEES)",
                "type": "ETF",
                "allocation_hint": "15% of total portfolio",
                "why": "Hedge against equity volatility and inflation shocks.",
                "expected_return_range_annual": "6% - 9%"
            },
        ]
