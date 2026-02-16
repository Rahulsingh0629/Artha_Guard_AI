from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from app.database.models import User, Portfolio
from app.auth.jwt_manager import get_current_user
from app.agents.portfolio_analyzer.analyzer import PortfolioAnalyzer, MarketDataService
from datetime import datetime, timezone

router = APIRouter()

class PortfolioAddRequest(BaseModel):
    symbol: str
    quantity: int
    buy_price: float
    sector: str = "Unknown"
    buy_datetime: datetime | None = None


def normalize_utc(dt: datetime | None) -> datetime | None:
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)

@router.post("/add")
async def add_stock(
    stock: PortfolioAddRequest,
    current_user: User = Depends(get_current_user)
):
    symbol = stock.symbol.strip().upper()
    if not symbol:
        raise HTTPException(status_code=400, detail="Stock symbol is required")
    if stock.quantity <= 0:
        raise HTTPException(status_code=400, detail="Quantity must be greater than 0")
    if stock.buy_price <= 0:
        raise HTTPException(status_code=400, detail="Buy price must be greater than 0")
    normalized_buy_datetime = normalize_utc(stock.buy_datetime)
    if normalized_buy_datetime and normalized_buy_datetime > datetime.now(timezone.utc):
        raise HTTPException(status_code=400, detail="Buy datetime cannot be in the future")

    market_service = MarketDataService()
    is_valid, live_price = market_service.validate_symbol(symbol)
    if not is_valid:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid or unsupported stock symbol: {symbol}"
        )

    warnings = []
    if live_price is not None:
        try:
            current_price = float(live_price)
            diff_ratio = abs((stock.buy_price - current_price) / current_price)
            buy_dt_for_check = normalized_buy_datetime or datetime.now(timezone.utc)
            age_days = (datetime.now(timezone.utc) - buy_dt_for_check).days
            if age_days <= 7 and diff_ratio > 0.35:
                warnings.append(
                    "Buy price differs significantly from current market price for a recent trade. "
                    "Please verify quantity/price/date or upload broker statement."
                )
        except Exception:
            pass

    new_stock = Portfolio(
        user_email=current_user.email,   
        stock_symbol=symbol,
        quantity=stock.quantity,
        average_buy_price=stock.buy_price,
        sector=stock.sector,
        buy_datetime=normalized_buy_datetime,
    )
    
    await new_stock.create()
    
    return {
        "status": "Stock added successfully",
        "symbol": symbol,
        "live_price": live_price,
        "warnings": warnings,
    }

@router.get("/analyze")
async def get_portfolio_analysis(
    current_user: User = Depends(get_current_user)
):
   
    analyzer = PortfolioAnalyzer()
    
    report = await analyzer.analyze_holdings(user_email=current_user.email)
    
    return report


class PortfolioDeleteRequest(BaseModel):
    symbol: str

@router.delete("/delete")
async def delete_stock(
    payload: PortfolioDeleteRequest,
    current_user: User = Depends(get_current_user)
):
    symbol = payload.symbol.strip().upper()
    if not symbol:
        raise HTTPException(status_code=400, detail="Stock symbol is required")

    holding = await Portfolio.find_one(
        Portfolio.user_email == current_user.email,
        Portfolio.stock_symbol == symbol
    )
    if not holding:
        raise HTTPException(status_code=404, detail=f"{symbol} not found in portfolio")

    await holding.delete()
    return {"status": "Stock deleted successfully", "symbol": symbol}
