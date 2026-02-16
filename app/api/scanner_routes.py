import asyncio
import time
from typing import Any

import requests
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.agents.intraday_scanner.probability_ranker import FinancialAdvisorAgent
from app.agents.intraday_scanner.scanner import MarketScanner
from app.auth.jwt_manager import get_current_user
from app.database.models import User, UserScannerWatchlist

router = APIRouter()

BASE_URL = "https://www.nseindia.com"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
    "Accept": "application/json",
    "Accept-Language": "en-US,en;q=0.9",
    "Referer": "https://www.nseindia.com",
    "Connection": "keep-alive",
}
UNIVERSE_CACHE: dict[str, Any] = {"symbols": [], "ts": 0.0}
UNIVERSE_CACHE_TTL = 60 * 30


class ChatRequest(BaseModel):
    user_id: str = "web_user"
    message: str


class ChatResponse(BaseModel):
    response: str
    data_source: str = "ArthaGuard AI Engine"


advisor_agent = FinancialAdvisorAgent()


def create_session() -> requests.Session:
    session = requests.Session()
    session.headers.update(HEADERS)
    home = session.get(BASE_URL, timeout=10)
    if home.status_code != 200:
        raise Exception("Failed to initialize NSE session")
    return session


def _fetch_universe_symbols() -> list[str]:
    cached_symbols = UNIVERSE_CACHE.get("symbols", [])
    cached_ts = float(UNIVERSE_CACHE.get("ts", 0.0))
    if cached_symbols and (time.time() - cached_ts) < UNIVERSE_CACHE_TTL:
        return list(cached_symbols)

    session = create_session()
    symbols: set[str] = set()

    # Try broad market first.
    try:
        pre_open = session.get(
            f"{BASE_URL}/api/market-data-pre-open?key=ALL",
            timeout=12,
        ).json()
        for item in pre_open.get("data", []):
            symbol = item.get("metadata", {}).get("symbol")
            if symbol and isinstance(symbol, str):
                symbols.add(symbol.upper())
    except Exception:
        pass

    # Fallback to NIFTY 500 if broad endpoint is unavailable.
    if not symbols:
        data = session.get(
            f"{BASE_URL}/api/equity-stockIndices?index=NIFTY%20500",
            timeout=12,
        ).json()
        for item in data.get("data", []):
            symbol = item.get("symbol")
            if symbol and isinstance(symbol, str):
                symbols.add(symbol.upper())

    universe = sorted(symbols)
    if not universe:
        raise Exception("Unable to fetch market stock universe")

    UNIVERSE_CACHE["symbols"] = universe
    UNIVERSE_CACHE["ts"] = time.time()
    return universe


@router.post("/chat", response_model=ChatResponse)
async def chat_endpoint(request: ChatRequest):
    try:
        ai_reply = advisor_agent.get_response(request.message)
        return ChatResponse(response=ai_reply)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/scan/market")
async def scan_market(
    page: int = 1,
    page_size: int = 20,
    current_user: User = Depends(get_current_user),
):
    safe_page = max(page, 1)
    safe_page_size = min(max(page_size, 10), 50)

    try:
        all_symbols = _fetch_universe_symbols()
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))

    watchlist_docs = await UserScannerWatchlist.find(
        UserScannerWatchlist.user_email == current_user.email
    ).to_list()
    watchlist_symbols = [w.stock_symbol.upper() for w in watchlist_docs]
    watchlist_set = set(watchlist_symbols)

    # Keep user's watchlist symbols at the top, then remaining universe.
    ordered_symbols = [s for s in watchlist_symbols if s in all_symbols] + [
        s for s in all_symbols if s not in watchlist_set
    ]

    total = len(ordered_symbols)
    start = (safe_page - 1) * safe_page_size
    end = start + safe_page_size
    symbols_page = ordered_symbols[start:end]

    scanner = MarketScanner()
    scan_results = await asyncio.to_thread(scanner.scan_watchlist, symbols_page)
    by_symbol = {str(item.get("symbol", "")).upper(): item for item in scan_results}

    items = []
    for symbol in symbols_page:
        result = by_symbol.get(symbol, {"symbol": symbol, "error": "No data available"})
        items.append(
            {
                "symbol": symbol,
                "is_watchlist": symbol in watchlist_set,
                "current_price": result.get("current_price"),
                "trend": result.get("trend"),
                "rsi": result.get("rsi"),
                "volatility_score": result.get("volatility_score"),
                "volume_change_pct": result.get("volume_change_pct"),
                "last_updated": result.get("last_updated"),
                "error": result.get("error"),
            }
        )

    total_pages = (total + safe_page_size - 1) // safe_page_size if total else 1
    return {
        "items": items,
        "page": safe_page,
        "page_size": safe_page_size,
        "total": total,
        "total_pages": total_pages,
        "watchlist_count": len(watchlist_symbols),
    }


@router.get("/watchlist")
async def get_watchlist(current_user: User = Depends(get_current_user)):
    docs = await UserScannerWatchlist.find(
        UserScannerWatchlist.user_email == current_user.email
    ).to_list()
    symbols = sorted([d.stock_symbol.upper() for d in docs])
    return {"symbols": symbols, "count": len(symbols)}


@router.post("/watchlist/{symbol}")
async def add_to_watchlist(symbol: str, current_user: User = Depends(get_current_user)):
    clean_symbol = symbol.strip().upper()
    if not clean_symbol:
        raise HTTPException(status_code=400, detail="Symbol is required")

    exists = await UserScannerWatchlist.find_one(
        UserScannerWatchlist.user_email == current_user.email,
        UserScannerWatchlist.stock_symbol == clean_symbol,
    )
    if not exists:
        await UserScannerWatchlist(
            user_email=current_user.email,
            stock_symbol=clean_symbol,
        ).create()

    return {"status": "added", "symbol": clean_symbol}


@router.delete("/watchlist/{symbol}")
async def remove_from_watchlist(symbol: str, current_user: User = Depends(get_current_user)):
    clean_symbol = symbol.strip().upper()
    if not clean_symbol:
        raise HTTPException(status_code=400, detail="Symbol is required")

    existing = await UserScannerWatchlist.find_one(
        UserScannerWatchlist.user_email == current_user.email,
        UserScannerWatchlist.stock_symbol == clean_symbol,
    )
    if existing:
        await existing.delete()

    return {"status": "removed", "symbol": clean_symbol}
