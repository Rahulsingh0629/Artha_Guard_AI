import re
from typing import Optional

from app.agents.intraday_scanner.scanner import MarketScanner


class FinancialAdvisorAgent:
    """
    ArthaGuard AI Advisor.
    Converts technical scanner output into buy/no-buy guidance with rationale.
    """

    def __init__(self):
        self.scanner = MarketScanner()

    def get_response(self, user_query: str) -> str:
        symbol = self._extract_stock_symbol(user_query)
        if not symbol:
            return (
                "Please mention a stock name or ticker. Example: "
                "'Should I buy RELIANCE?' or 'Buy Tata Motors?'"
            )

        analysis = self.scanner.analyze_stock(symbol)
        if "error" in analysis:
            return f"I couldn't fetch data for {symbol}. Reason: {analysis.get('error')}"

        verdict = self._build_verdict(analysis)
        return verdict

    def _extract_stock_symbol(self, query: str) -> Optional[str]:
        q = str(query or "").upper().strip()
        if not q:
            return None

        alias_map = {
            "RELIANCE": "RELIANCE",
            "TATA STEEL": "TATASTEEL",
            "TATASTEEL": "TATASTEEL",
            "TATA MOTORS": "TATAMOTORS",
            "TATAMOTORS": "TATAMOTORS",
            "INFY": "INFY",
            "INFOSYS": "INFY",
            "HDFC": "HDFCBANK",
            "HDFCBANK": "HDFCBANK",
            "SBI": "SBIN",
            "SBIN": "SBIN",
            "ICICI": "ICICIBANK",
            "ICICIBANK": "ICICIBANK",
            "WIPRO": "WIPRO",
            "TCS": "TCS",
            "ITC": "ITC",
            "LT": "LT",
            "BAJFINANCE": "BAJFINANCE",
        }

        for key, value in alias_map.items():
            if key in q:
                return value

        tokens = re.findall(r"[A-Z]{2,15}", q)
        stop = {"SHOULD", "BUY", "SELL", "TODAY", "STOCK", "CAN", "I", "YOU", "ANY"}
        for token in tokens:
            if token not in stop:
                return token
        return None

    def _build_verdict(self, data: dict) -> str:
        symbol = data.get("symbol", "N/A")
        price = float(data.get("current_price", 0) or 0)
        rsi = float(data.get("rsi", 50) or 50)
        trend = str(data.get("trend", "SIDEWAYS") or "SIDEWAYS").upper()
        volume = float(data.get("volume_change_pct", 0) or 0)
        volatility = float(data.get("volatility_score", 0) or 0)

        # Heuristic scoring for short-term directional bias.
        bullish_points = 0.0
        bearish_points = 0.0

        if trend == "BULLISH":
            bullish_points += 2.2
        elif trend == "BEARISH":
            bearish_points += 2.2
        else:
            bullish_points += 0.8
            bearish_points += 0.8

        if rsi < 32:
            bullish_points += 1.8
        elif rsi > 70:
            bearish_points += 1.8
        elif 45 <= rsi <= 60:
            bullish_points += 1.0

        if volume > 20:
            if trend == "BULLISH":
                bullish_points += 1.4
            elif trend == "BEARISH":
                bearish_points += 1.4

        if volatility > 0.09:
            bearish_points += 1.1
        elif volatility < 0.05:
            bullish_points += 0.7

        net_edge = bullish_points - bearish_points
        estimated_upside_pct = max(0.5, min(12.0, 2.8 + net_edge * 1.8))
        estimated_downside_pct = max(0.5, min(12.0, 2.3 + (-net_edge) * 1.8))

        expected_up_price = round(price * (1 + estimated_upside_pct / 100), 2) if price else None
        expected_down_price = round(price * (1 - estimated_downside_pct / 100), 2) if price else None

        if net_edge >= 1.4 and rsi <= 65:
            recommendation = "BUY"
            reason = "Bullish setup with favorable risk-reward."
        elif net_edge <= -1.0 or rsi >= 72:
            recommendation = "NO BUY"
            reason = "Risk of correction or weak setup is high."
        else:
            recommendation = "WAIT"
            reason = "Signal quality is mixed; wait for clearer confirmation."

        return (
            f"Analysis for {symbol}\n"
            f"Current Price: {price}\n"
            f"Trend: {trend} | RSI: {rsi} | Volume Change: {volume}% | Volatility: {volatility}\n"
            f"Estimated Profit Scenario: +{round(estimated_upside_pct, 2)}% (Target ~ {expected_up_price})\n"
            f"Estimated Loss Scenario: -{round(estimated_downside_pct, 2)}% (Risk ~ {expected_down_price})\n"
            f"Recommendation: {recommendation}\n"
            f"Why: {reason}\n"
            f"Note: This is technical-probability guidance, not guaranteed returns."
        )
