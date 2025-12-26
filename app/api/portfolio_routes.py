from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

# [CHANGE 1] No SQL Session imports
from app.database.models import User, Portfolio
from app.auth.jwt_manager import get_current_user
from app.agents.portfolio_analyzer.analyzer import PortfolioAnalyzer

router = APIRouter()

# --- INPUT SCHEMA ---
class PortfolioAddRequest(BaseModel):
    symbol: str
    quantity: int
    buy_price: float
    sector: str = "Unknown"

# --- ROUTE 1: Add Stock (Async for MongoDB) ---
@router.post("/add")
async def add_stock(
    stock: PortfolioAddRequest,
    current_user: User = Depends(get_current_user)
):
    """
    Adds a stock to the user's portfolio.
    """
    # [CHANGE 2] Create Beanie Document (No db.add/commit needed)
    new_stock = Portfolio(
        user_email=current_user.email,  # Use email to link, not ID
        stock_symbol=stock.symbol.upper(),
        quantity=stock.quantity,
        average_buy_price=stock.buy_price,
        sector=stock.sector
    )
    
    # [CHANGE 3] Async Save
    await new_stock.create()
    
    return {"status": "Stock added successfully", "symbol": stock.symbol}

# --- ROUTE 2: Get Analysis (Async) ---
@router.get("/analyze")
async def get_portfolio_analysis(
    current_user: User = Depends(get_current_user)
):
    """
    Returns P&L and Sector breakdown.
    """
    analyzer = PortfolioAnalyzer()
    
    # [CHANGE 4] Call the async analyzer with email
    report = await analyzer.analyze_holdings(user_email=current_user.email)
    
    return report