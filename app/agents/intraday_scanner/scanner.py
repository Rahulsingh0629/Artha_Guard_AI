try:
    import yfinance as yf
except Exception:
    yf = None
import concurrent.futures
import pandas as pd
from datetime import datetime
from typing import Dict, Any, List
from app.agents.intraday_scanner.indicators import TechnicalIndicators  # Import from local file

class MarketScanner:
    """
    Fetches live market data and runs technical analysis.
    """
    
    def analyze_stock(self, symbol: str) -> Dict[str, Any]:
        try:
            if yf is None:
                return {"error": "Market data provider unavailable: yfinance not installed"}

            ticker_sym = f"{symbol}.NS" if not symbol.endswith(".NS") else symbol
            stock = yf.Ticker(ticker_sym)
            
            # Fetch 3 months of data to ensure valid moving averages
            hist = stock.history(period="3mo")
            if hist.empty:
                return {"error": "No data found"}

            # Apply Math from indicators.py
            df = TechnicalIndicators.add_all_indicators(hist)
            
            latest = df.iloc[-1]
            prev = df.iloc[-2]

            # Determine basic trend state
            trend = "SIDEWAYS"
            if latest['MACD'] > latest['Signal_Line']: trend = "BULLISH"
            elif latest['MACD'] < latest['Signal_Line']: trend = "BEARISH"

            bb_width = (latest['Upper_Band'] - latest['Lower_Band']) / latest['SMA_20']
            
            return {
                "symbol": symbol,
                "current_price": round(latest['Close'], 2),
                "trend": trend,
                "rsi": round(latest['RSI'], 2),
                "volatility_score": round(bb_width, 4),
                "volume_change_pct": round(((latest['Volume'] - prev['Volume']) / prev['Volume']) * 100, 1),
                "last_updated": datetime.now().isoformat()
            }
        except Exception as e:
            return {"error": str(e)}

    def scan_watchlist(self, symbols: List[str]) -> List[Dict]:
        """Runs analysis in parallel."""
        results = []
        with concurrent.futures.ThreadPoolExecutor() as executor:
            future_to_stock = {executor.submit(self.analyze_stock, s): s for s in symbols}
            for future in concurrent.futures.as_completed(future_to_stock):
                res = future.result()
                if "error" not in res:
                    results.append(res)
        return results
