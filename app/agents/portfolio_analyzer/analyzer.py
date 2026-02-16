import logging
import requests
import time
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime, timezone
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
    BASE_URL = "https://www.nseindia.com"
    HEADERS = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
        "Accept": "application/json",
        "Accept-Language": "en-US,en;q=0.9",
        "Referer": "https://www.nseindia.com",
        "Connection": "keep-alive",
    }
    CACHE_TTL_SECONDS = 5.0
    _price_cache: Dict[str, Tuple[float, float]] = {}

    def __init__(self):
        self.session: Optional[requests.Session] = None

    @staticmethod
    def _normalize_symbol(symbol: str) -> str:
        cleaned = str(symbol or "").strip().upper()
        return cleaned[:-3] if cleaned.endswith(".NS") else cleaned

    @staticmethod
    def _to_float(value: Any) -> Optional[float]:
        if value is None:
            return None
        if isinstance(value, (int, float)):
            return float(value)
        if isinstance(value, str):
            try:
                return float(value.replace(",", "").strip())
            except ValueError:
                return None
        return None

    def _create_session(self) -> requests.Session:
        session = requests.Session()
        session.headers.update(self.HEADERS)
        home = session.get(self.BASE_URL, timeout=10)
        if home.status_code != 200:
            raise RuntimeError("Failed to initialize NSE session")
        return session

    def _get_session(self, force_refresh: bool = False) -> requests.Session:
        if force_refresh or self.session is None:
            self.session = self._create_session()
        return self.session

    def fetch_live_price(self, symbol: str) -> Optional[float]:
        """Fetch one symbol price directly from NSE quote endpoint."""
        normalized = self._normalize_symbol(symbol)
        if not normalized:
            return None

        cached = self._price_cache.get(normalized)
        now = time.time()
        if cached and (now - cached[1] <= self.CACHE_TTL_SECONDS):
            return cached[0]

        for force_refresh in (False, True):
            try:
                session = self._get_session(force_refresh=force_refresh)
                res = session.get(
                    f"{self.BASE_URL}/api/quote-equity",
                    params={"symbol": normalized},
                    timeout=10,
                )
                if res.status_code != 200:
                    continue
                data = res.json()
                price_info = data.get("priceInfo") or {}
                price = self._to_float(price_info.get("lastPrice"))
                if price is None:
                    continue
                self._price_cache[normalized] = (price, now)
                return price
            except Exception as e:
                logger.error(f"NSE fetch error for {normalized}: {e}")

        return None

    def validate_symbol(self, symbol: str) -> Tuple[bool, Optional[float]]:
        """Returns whether symbol is tradeable on NSE and current price."""
        price = self.fetch_live_price(symbol)
        return (price is not None, price)

    def fetch_live_prices(self, symbols: List[str]) -> Dict[str, float]:
        """Fetches prices from NSE for a list of symbols."""
        results: Dict[str, float] = {}
        for raw_symbol in symbols:
            normalized = self._normalize_symbol(raw_symbol)
            if not normalized:
                continue
            price = self.fetch_live_price(normalized)
            if price is not None:
                results[normalized] = price
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
        analysis_as_of = datetime.now(timezone.utc)
        live_price_count = 0
        fallback_price_count = 0
        fallback_symbols: List[str] = []

        for item in db_holdings:
            symbol = item.stock_symbol
            sector = item.sector if item.sector else "Unknown"
            
            # [CHANGE 4] No explicit casting needed, Beanie handles types
            qty = Decimal(item.quantity)
            buy_price = Decimal(item.average_buy_price)
            
            # Get Live Price
            live_price_float = live_price_map.get(symbol)
            if live_price_float is None:
                retry_price = self.market_service.fetch_live_price(symbol)
                if retry_price is None:
                    live_price = buy_price
                    price_source = "FALLBACK_BUY_PRICE"
                    fallback_price_count += 1
                    fallback_symbols.append(symbol)
                else:
                    live_price = Decimal(str(retry_price))
                    price_source = "NSE_LIVE"
                    live_price_count += 1
            else:
                live_price = Decimal(str(live_price_float))
                price_source = "NSE_LIVE"
                live_price_count += 1

            current_val = qty * live_price
            invested_val = qty * buy_price
            
            total_invested += invested_val
            total_current_value += current_val

            # Tax Calculation (Now item.created_at exists!)
            effective_buy_datetime = item.buy_datetime or item.created_at or datetime.now(timezone.utc)
            if effective_buy_datetime.tzinfo is None:
                effective_buy_datetime = effective_buy_datetime.replace(tzinfo=timezone.utc)

            tax_report = self.tax_engine.calculate_tax(
                buy_date=effective_buy_datetime,
                quantity=int(qty),
                buy_price=float(buy_price),
                current_price=float(live_price),
                asset_type=AssetType.EQUITY_DELIVERY 
            )
            holding_days = max((analysis_as_of - effective_buy_datetime).days, 0)
            pnl_value = current_val - invested_val
            pnl_percent = float((pnl_value / invested_val) * Decimal("100")) if invested_val > 0 else 0.0

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
                "pnl": float(pnl_value),
                "pnl_percent": pnl_percent,
                "buy_datetime": effective_buy_datetime.isoformat(),
                "price_as_of": analysis_as_of.isoformat(),
                "price_source": price_source,
                "holding_days": holding_days,
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
                "total_pnl_percent": float(
                    ((total_current_value - total_invested) / total_invested) * Decimal("100")
                ) if total_invested > 0 else 0.0,
                "as_of": analysis_as_of.isoformat(),
            },
            "risk_profile": {
                "score": risk_report.overall_score,
                "level": risk_report.overall_level.value,
                "alerts": risk_report.alerts
            },
            "meta": {
                "price_source": "NSE_QUOTE_EQUITY",
                "analysis_as_of": analysis_as_of.isoformat(),
                "data_quality": {
                    "live_price_count": live_price_count,
                    "fallback_price_count": fallback_price_count,
                    "fallback_symbols": fallback_symbols,
                },
            },
            "holdings": analyzed_positions
        }

    def _build_empty_response(self):
        return {
            "summary": {
                "total_investment": 0,
                "current_value": 0,
                "total_pnl": 0,
                "total_pnl_percent": 0,
                "as_of": datetime.now(timezone.utc).isoformat(),
            },
            "risk_profile": {"score": 0, "level": "LOW", "alerts": []},
            "meta": {
                "price_source": "NSE_QUOTE_EQUITY",
                "analysis_as_of": datetime.now(timezone.utc).isoformat(),
                "data_quality": {
                    "live_price_count": 0,
                    "fallback_price_count": 0,
                    "fallback_symbols": [],
                },
            },
            "holdings": []
        }
