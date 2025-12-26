import numpy as np

class ScenarioSimulator:
    
    def simulate_wealth(self, current_investment: float, monthly_sip: float, years: int = 10):
        """
        Runs a Monte Carlo simulation to predict future wealth range.
        """
        if current_investment <= 0 and monthly_sip <= 0:
            return {"error": "No investment data to simulate."}

        # Market Assumptions (Nifty 50 Historical)
        avg_return = 0.12  # 12% annual return
        volatility = 0.15  # 15% standard deviation
        
        simulations = 1000 # Run 1000 different market scenarios
        results = []
        
        for _ in range(simulations):
            wealth = current_investment
            for _ in range(years):
                # Random market return for this year
                annual_return = np.random.normal(avg_return, volatility)
                wealth = wealth * (1 + annual_return) + (monthly_sip * 12)
            results.append(wealth)
            
        # Analyze Results
        worst_case = np.percentile(results, 5)   # Bottom 5% luck
        average_case = np.mean(results)          # Most likely
        best_case = np.percentile(results, 95)   # Top 5% luck (Bull run)
        
        return {
            "years": years,
            "worst_case_scenario": round(worst_case, 2),
            "likely_scenario": round(average_case, 2),
            "best_case_scenario": round(best_case, 2),
            "insight": f"In 95% of cases, your wealth will grow to at least ₹{round(worst_case, 2)}"
        }