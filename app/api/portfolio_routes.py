from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from app.database.models import User, Portfolio
from app.auth.jwt_manager import get_current_user
from app.agents.portfolio_analyzer.analyzer import PortfolioAnalyzer

router = APIRouter()

class PortfolioAddRequest(BaseModel):
    symbol: str
    quantity: int
    buy_price: float
    sector: str = "Unknown"

@router.post("/add")
async def add_stock(
    stock: PortfolioAddRequest,
    current_user: User = Depends(get_current_user)
):
    new_stock = Portfolio(
        user_email=current_user.email,   
        stock_symbol=stock.symbol.upper(),
        quantity=stock.quantity,
        average_buy_price=stock.buy_price,
        sector=stock.sector
    )
    
    await new_stock.create()
    
    return {"status": "Stock added successfully", "symbol": stock.symbol}

@router.get("/analyze")
async def get_portfolio_analysis(
    current_user: User = Depends(get_current_user)
):
   
    analyzer = PortfolioAnalyzer()
    
    report = await analyzer.analyze_holdings(user_email=current_user.email)
    
    return report