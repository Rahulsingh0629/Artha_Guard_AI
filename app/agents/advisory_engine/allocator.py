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