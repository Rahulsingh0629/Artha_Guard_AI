import concurrent.futures
import logging
import yfinance as yf
from typing import List, Dict, Any, Optional
from datetime import datetime
from decimal import Decimal
from dataclasses import dataclass

# [CHANGE 1] Import Beanie Model, NOT SQLAlchemy
from app.database.models import Portfolio
from app.agents.portfolio_analyzer.tax_engine import AdvancedTaxEngine, AssetType
from app.agents.portfolio_analyzer.risk_engine import AdvancedRiskEngine

@dataclass
class PortfolioPosition:
    ticker: str
    sector: str
    current_value: Decimal
    beta: float = 1.0

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("ArthaGuardAnalyzer")

class MarketDataService:
    @staticmethod
    def fetch_live_prices(symbols: List[str]) -> Dict[str, float]:
        """Fetches prices in parallel."""
        results = {}
        formatted_symbols = [f"{s}.NS" if not s.endswith(".NS") else s for s in symbols]

        def fetch_single(ticker_symbol):
            try:
                ticker = yf.Ticker(ticker_symbol)
                price = ticker.fast_info.get('last_price', None)
                clean_symbol = ticker_symbol.replace(".NS", "")
                return clean_symbol, price
            except Exception as e:
                logger.error(f"Error fetching {ticker_symbol}: {e}")
                return ticker_symbol.replace(".NS", ""), None

        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            future_to_stock = {executor.submit(fetch_single, s): s for s in formatted_symbols}
            for future in concurrent.futures.as_completed(future_to_stock):
                symbol, price = future.result()
                if price:
                    results[symbol] = price
        return results

class PortfolioAnalyzer:
    def __init__(self):
        self.tax_engine = AdvancedTaxEngine()
        self.risk_engine = AdvancedRiskEngine()
        self.market_service = MarketDataService()

    # [CHANGE 2] Made function ASYNC and removed 'db: Session'
    async def analyze_holdings(self, user_email: str) -> Dict[str, Any]:
        
        # [CHANGE 3] Use Beanie Query Syntax
        db_holdings = await Portfolio.find(Portfolio.user_email == user_email).to_list()
        
        if not db_holdings:
            return self._build_empty_response()

        # Extract symbols
        symbols = [h.stock_symbol for h in db_holdings]
        live_price_map = self.market_service.fetch_live_prices(symbols)

        analyzed_positions = []
        risk_input_positions = [] 

        total_invested = Decimal("0.00")
        total_current_value = Decimal("0.00")

        for item in db_holdings:
            symbol = item.stock_symbol
            sector = item.sector if item.sector else "Unknown"
            
            # [CHANGE 4] No explicit casting needed, Beanie handles types
            qty = Decimal(item.quantity)
            buy_price = Decimal(item.average_buy_price)
            
            # Get Live Price
            live_price_float = live_price_map.get(symbol)
            if live_price_float is None:
                live_price = buy_price
            else:
                live_price = Decimal(str(live_price_float))

            current_val = qty * live_price
            invested_val = qty * buy_price
            
            total_invested += invested_val
            total_current_value += current_val

            # Tax Calculation (Now item.created_at exists!)
            tax_report = self.tax_engine.calculate_tax(
                buy_date=item.created_at or datetime.now(),
                quantity=int(qty),
                buy_price=float(buy_price),
                current_price=float(live_price),
                asset_type=AssetType.EQUITY_DELIVERY 
            )

            # Prepare for Risk Engine
            risk_input_positions.append(
                PortfolioPosition(
                    ticker=symbol,
                    sector=sector,
                    current_value=current_val,
                    beta=1.0 
                )
            )

            # Build UI Data
            analyzed_positions.append({
                "symbol": symbol,
                "sector": sector,
                "qty": int(qty),
                "buy_price": float(buy_price),
                "current_price": float(live_price),
                "invested_value": float(invested_val),
                "current_value": float(current_val),
                "pnl": float(current_val - invested_val),
                "tax_analysis": {
                    "type": tax_report.period_type,
                    "estimated_tax": float(tax_report.total_tax)
                }
            })

        # Run Risk Analysis
        risk_report = self.risk_engine.analyze_portfolio(risk_input_positions)

        return {
            "summary": {
                "total_investment": float(total_invested),
                "current_value": float(total_current_value),
                "total_pnl": float(total_current_value - total_invested),
            },
            "risk_profile": {
                "score": risk_report.overall_score,
                "level": risk_report.overall_level.value,
                "alerts": risk_report.alerts
            },
            "holdings": analyzed_positions
        }

    def _build_empty_response(self):
        return {
            "summary": {"total_investment": 0, "current_value": 0, "total_pnl": 0},
            "risk_profile": {"level": "LOW", "alerts": []},
            "holdings": []
        }