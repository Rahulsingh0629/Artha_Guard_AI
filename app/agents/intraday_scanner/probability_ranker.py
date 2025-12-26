from typing import Optional  # <--- 1. Import Optional
from app.agents.intraday_scanner.scanner import MarketScanner

class FinancialAdvisorAgent:
    """
    ArthaGuard AI Agent.
    Interprets technical data into human-readable advice (RAG Pattern).
    """
    def __init__(self):
        self.scanner = MarketScanner()

    def get_response(self, user_query: str) -> str:
        # 1. Intent Recognition
        stock_symbol = self._extract_stock_symbol(user_query)
        
        if not stock_symbol:
            return "I am ArthaGuard AI. Ask me about a stock like 'Reliance' or 'Tata Steel'."

        # 2. Tool Execution (Get Data)
        analysis = self.scanner.analyze_stock(stock_symbol)
        
        if "error" in analysis:
            return f"I couldn't fetch data for {stock_symbol}. Please try again later."

        # 3. Probability & Ranking Logic
        advice = self._generate_verdict(analysis)
        
        return f"""
**Analysis for {stock_symbol}**
Price: ₹{analysis['current_price']}

**AI Verdict:** {advice}

*Key Indicators:*
- Trend: {analysis['trend']}
- RSI: {analysis['rsi']}
"""

    def _generate_verdict(self, data: dict) -> str:
        """Decides the probability of a move based on indicators."""
        rsi = data['rsi']
        trend = data['trend']
        
        if rsi > 70:
            return "High probability of correction. The stock is **Overbought**."
        elif rsi < 30:
            return "High probability of reversal. The stock is **Oversold** (Value Buy)."
        elif trend == "BULLISH" and rsi > 50:
            return "Strong Momentum. The trend is positive."
        else:
            return "Market is undecided. Wait for a clearer signal."

    # --- THE FIX IS BELOW ---
    def _extract_stock_symbol(self, query: str) -> Optional[str]: 
        """
        Returns a Ticker string if found, otherwise returns None.
        """
        query = query.upper()
        common_map = {
            "RELIANCE": "RELIANCE", "TATA STEEL": "TATASTEEL", "INFY": "INFY",
            "HDFC": "HDFCBANK", "SBI": "SBIN"
        }
        for name, ticker in common_map.items():
            if name in query:
                return ticker
        
        return None # Now valid because return type is Optional[str]