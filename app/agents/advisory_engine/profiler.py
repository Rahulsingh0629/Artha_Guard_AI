from typing import Dict

class UserProfiler:
    
    def analyze_profile(self, age: int, income: float, savings_rate: float) -> Dict[str, str]:
        """
        Determines the User's Risk Profile using a weighted scoring model.
        """
        score = 0
        
        # Age Factor (Younger = More Risk Capacity)
        if age < 25: score += 40
        elif age < 35: score += 30
        elif age < 50: score += 20
        else: score += 10
        
        # Wealth Factor (Higher Income = More Risk Capacity)
        # Using Indian Income brackets (Annual)
        if income > 2000000: score += 30  # > 20L
        elif income > 1000000: score += 20 # > 10L
        else: score += 10
        
        # Savings Factor
        if savings_rate > 0.30: score += 20 # Saves >30%
        elif savings_rate > 0.10: score += 10
        
        # Determine Category
        if score >= 80:
            return {"risk_category": "AGGRESSIVE", "description": "High growth focus. Small/Mid Cap stocks."}
        elif score >= 50:
            return {"risk_category": "MODERATE", "description": "Balanced growth. Nifty 50 + Gold."}
        else:
            return {"risk_category": "CONSERVATIVE", "description": "Capital protection. FD + Debt Funds."}