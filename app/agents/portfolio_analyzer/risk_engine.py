from dataclasses import dataclass, field
from typing import List, Dict, Tuple
from decimal import Decimal
from collections import defaultdict
from enum import Enum
import math

# --- 1. Domain Models ---

class RiskLevel(Enum):
    LOW = "LOW"
    MODERATE = "MODERATE"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"

@dataclass
class PortfolioPosition:
    """Represents a single holding in the portfolio."""
    ticker: str
    sector: str
    current_value: Decimal
    beta: float = 1.0  # Default to 1.0 (moves with market) if unknown

@dataclass
class RiskMetric:
    """Granular detail for a specific risk factor."""
    score: float  # 0 to 100
    level: RiskLevel
    details: List[str]

@dataclass
class RiskReport:
    """Comprehensive output of the risk analysis."""
    overall_score: int  # 0 (Safe) to 100 (Risky)
    overall_level: RiskLevel
    diversification_hhi: float
    portfolio_beta: float
    metrics: Dict[str, RiskMetric]
    alerts: List[str]

# --- 2. The Engine ---

class AdvancedRiskEngine:
    
    # Configuration Thresholds (Configurable via DB or injection)
    HHI_THRESHOLDS = {1500: RiskLevel.LOW, 2500: RiskLevel.MODERATE, 10000: RiskLevel.HIGH}
    SINGLE_STOCK_LIMIT = Decimal("0.15")  # 15% max in one stock
    SECTOR_LIMIT = Decimal("0.30")        # 30% max in one sector

    def analyze_portfolio(self, holdings: List[PortfolioPosition]) -> RiskReport:
        if not holdings:
            return self._empty_portfolio_report()

        total_value = sum((h.current_value for h in holdings), Decimal("0"))
        
        # 1. Calculate Weights
        weights = {h.ticker: (h.current_value / total_value) for h in holdings}
        
        # 2. Analyze Components
        concentration_risk = self._analyze_sector_concentration(holdings, total_value)
        stock_risk = self._analyze_single_stock_risk(weights)
        volatility_risk = self._calculate_weighted_beta(holdings, total_value)

        # 3. Synthesize Overall Score (Weighted Average of factors)
        # Weighting: Concentration (40%), Single Stock (30%), Volatility (30%)
        weighted_score = (
            (concentration_risk.score * 0.4) + 
            (stock_risk.score * 0.3) + 
            (volatility_risk.score * 0.3)
        )

        overall_level = self._get_risk_level_from_score(weighted_score)
        
        # Collect all alerts
        all_alerts = concentration_risk.details + stock_risk.details + volatility_risk.details

        return RiskReport(
            overall_score=int(weighted_score),
            overall_level=overall_level,
            diversification_hhi=concentration_risk.score, # Storing HHI/Score mapping loosely here
            portfolio_beta=float(volatility_risk.score) / 50.0, # Reverse engineer beta for display
            metrics={
                "sector_concentration": concentration_risk,
                "single_stock_exposure": stock_risk,
                "volatility": volatility_risk
            },
            alerts=all_alerts
        )

    def _analyze_sector_concentration(self, holdings: List[PortfolioPosition], total_val: Decimal) -> RiskMetric:
        """
        Uses Herfindahl-Hirschman Index (HHI) to measure sector concentration.
        HHI = Sum of (sector_weight * 100)^2
        Range: <1500 (Diverse), 1500-2500 (Moderate), >2500 (Concentrated)
        """
        sector_map = defaultdict(Decimal)
        for h in holdings:
            sector_map[h.sector] += h.current_value

        hhi_score = 0
        alerts = []
        
        for sector, val in sector_map.items():
            weight = val / total_val
            # Check hard limit
            if weight > self.SECTOR_LIMIT:
                alerts.append(f"Sector Overweight: {sector} constitutes {round(weight*100, 1)}% of portfolio.")
            
            # HHI Calculation: Sum of squared percentages
            hhi_score += (float(weight) * 100) ** 2

        # Normalize HHI (0-100 scale for internal scoring)
        # HHI usually maxes at 10,000 (100^2). We map 0-5000 to 0-100 risk score roughly.
        normalized_risk = min(100, hhi_score / 50) 
        
        level = RiskLevel.LOW
        if hhi_score > 2500: level = RiskLevel.HIGH
        elif hhi_score > 1500: level = RiskLevel.MODERATE

        return RiskMetric(score=normalized_risk, level=level, details=alerts)

    def _analyze_single_stock_risk(self, weights: Dict[str, Decimal]) -> RiskMetric:
        """Checks for idiosyncratic risk (putting all eggs in one basket)."""
        alerts = []
        max_exposure = Decimal("0")
        
        for ticker, weight in weights.items():
            if weight > max_exposure:
                max_exposure = weight
            if weight > self.SINGLE_STOCK_LIMIT:
                alerts.append(f"Concentration Risk: {ticker} is {round(weight*100, 1)}% of portfolio.")

        # Score: 0 if max is 5%, 100 if max is 100%
        risk_score = float(max_exposure) * 100
        
        level = RiskLevel.LOW
        if risk_score > 25: level = RiskLevel.HIGH
        elif risk_score > 15: level = RiskLevel.MODERATE

        return RiskMetric(score=risk_score, level=level, details=alerts)

    def _calculate_weighted_beta(self, holdings: List[PortfolioPosition], total_val: Decimal) -> RiskMetric:
        """
        Calculates Portfolio Beta.
        Beta > 1.0: More volatile than market (High Risk).
        Beta < 1.0: Less volatile (Low Risk).
        """
        weighted_beta = 0.0
        for h in holdings:
            weight = float(h.current_value / total_val)
            weighted_beta += (weight * h.beta)

        alerts = []
        if weighted_beta > 1.3:
            alerts.append(f"High Volatility: Portfolio Beta is {round(weighted_beta, 2)}.")
        
        # Map Beta to Risk Score (0-100)
        # Beta 1.0 = Score 50 (Market Average)
        # Beta 2.0 = Score 100 (High Risk)
        risk_score = min(100, weighted_beta * 50)
        
        level = RiskLevel.LOW
        if weighted_beta > 1.2: level = RiskLevel.HIGH
        elif weighted_beta > 0.9: level = RiskLevel.MODERATE

        return RiskMetric(score=risk_score, level=level, details=alerts)

    def _get_risk_level_from_score(self, score: float) -> RiskLevel:
        if score < 30: return RiskLevel.LOW
        if score < 60: return RiskLevel.MODERATE
        if score < 80: return RiskLevel.HIGH
        return RiskLevel.CRITICAL

    def _empty_portfolio_report(self):
        return RiskReport(0, RiskLevel.LOW, 0, 0, {}, ["Portfolio is empty"])

# --- 3. Usage Example ---

if __name__ == "__main__":
    engine = AdvancedRiskEngine()

    # Scenario: High concentration in IT, High Beta stocks
    my_portfolio = [
        PortfolioPosition("INFY", "IT", Decimal("450000"), beta=1.1),  # 45% IT
        PortfolioPosition("TCS", "IT", Decimal("150000"), beta=0.9),   # 15% IT
        PortfolioPosition("HDFCBANK", "Banking", Decimal("200000"), beta=1.05),
        PortfolioPosition("ADANIENT", "Metals", Decimal("200000"), beta=2.2), # High Beta
    ]

    report = engine.analyze_portfolio(my_portfolio)

    print(f"--- ArthaGuard Risk Report ---")
    print(f"Overall Risk Score: {report.overall_score}/100")
    print(f"Risk Level        : {report.overall_level.value}")
    print(f"Portfolio Beta    : {report.portfolio_beta:.2f}")
    print("\n--- Alerts ---")
    for alert in report.alerts:
        print(f"⚠️  {alert}")