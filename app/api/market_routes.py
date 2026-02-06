from fastapi import APIRouter, HTTPException
import requests
import time
from datetime import datetime

router = APIRouter()

# --------------------------------------------------
# NSE CONFIG
# --------------------------------------------------
BASE_URL = "https://www.nseindia.com"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
    "Accept": "application/json",
    "Accept-Language": "en-US,en;q=0.9",
    "Referer": "https://www.nseindia.com",
    "Connection": "keep-alive",
}

# --------------------------------------------------
# SIMPLE IN-MEMORY CACHE
# --------------------------------------------------
CACHE = {}
CACHE_TTL = 30  # seconds


def cache_get(key):
    if key in CACHE:
        data, ts = CACHE[key]
        if time.time() - ts < CACHE_TTL:
            return data
    return None


def cache_set(key, value):
    CACHE[key] = (value, time.time())


# --------------------------------------------------
# NSE SESSION (ANTI-BLOCK, HARDENED)
# --------------------------------------------------
def create_session():
    session = requests.Session()
    session.headers.update(HEADERS)

    home = session.get(BASE_URL, timeout=10)
    if home.status_code != 200:
        raise Exception("Failed to initialize NSE session")

    return session


# --------------------------------------------------
# 1️⃣ MARKET STATUS
# --------------------------------------------------
@router.get("/market-status")
def market_status():
    now = datetime.now()
    weekday = now.weekday()

    if weekday >= 5:
        return {"status": "CLOSED", "reason": "Weekend"}

    if now.hour < 9 or (now.hour == 9 and now.minute < 15):
        return {"status": "PRE_OPEN"}

    if now.hour > 15 or (now.hour == 15 and now.minute > 30):
        return {"status": "CLOSED"}

    return {"status": "OPEN"}


# --------------------------------------------------
# 2️⃣ ALL MAJOR INDICES
# --------------------------------------------------
@router.get("/indices")
def get_indices():
    cached = cache_get("indices")
    if cached:
        return cached

    try:
        session = create_session()
        res = session.get(f"{BASE_URL}/api/allIndices", timeout=10)

        data = res.json()
        if "data" not in data:
            raise Exception("Invalid indices response")

        REQUIRED = {
            "NIFTY 50": "nifty",
            "SENSEX": "sensex",
            "NIFTY BANK": "bankNifty",
            "NIFTY FIN SERVICE": "finNifty",
            "NIFTY MIDCAP 50": "midcap",
            "NIFTY SMALLCAP 50": "smallcap",
        }

        result = {}
        for i in data["data"]:
            if i.get("index") in REQUIRED:
                key = REQUIRED[i["index"]]
                result[key] = {
                    "name": i["index"],
                    "price": i.get("last"),
                    "change": i.get("change"),
                    "percent": i.get("percentChange"),
                }

        cache_set("indices", result)
        return result

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# --------------------------------------------------
# 3️⃣ ALL NIFTY-50 STOCKS
# --------------------------------------------------
@router.get("/stocks")
def get_all_stocks():
    cached = cache_get("stocks")
    if cached:
        return cached

    try:
        session = create_session()
        res = session.get(
            f"{BASE_URL}/api/equity-stockIndices?index=NIFTY%2050",
            timeout=10,
        )

        data = res.json()
        if "data" not in data or not isinstance(data["data"], list):
            raise Exception("Invalid stock data from NSE")

        result = []
        for s in data["data"]:
            result.append({
                "symbol": s.get("symbol"),
                "name": s.get("meta", {}).get("companyName", s.get("symbol")),
                "price": s.get("lastPrice"),
                "change": s.get("change"),
                "percent": s.get("pChange"),
                "open": s.get("open"),
                "high": s.get("dayHigh"),
                "low": s.get("dayLow"),
                "previousClose": s.get("previousClose"),
            })

        response = {"count": len(result), "stocks": result}
        cache_set("stocks", response)
        return response

    except Exception as e:
        print("🔥 STOCKS ERROR:", e)
        raise HTTPException(status_code=500, detail=str(e))


# --------------------------------------------------
# 4️⃣ TOP GAINERS & LOSERS
# --------------------------------------------------
@router.get("/top-movers")
def top_movers():
    cached = cache_get("top_movers")
    if cached:
        return cached

    try:
        session = create_session()
        res = session.get(
            f"{BASE_URL}/api/equity-stockIndices?index=NIFTY%2050",
            timeout=10,
        )

        data = res.json()
        if "data" not in data:
            raise Exception("Invalid top movers data")

        stocks_sorted = sorted(
            data["data"], key=lambda x: x.get("pChange", 0), reverse=True
        )

        response = {
            "gainers": [
                {"symbol": s.get("symbol"), "percent": s.get("pChange")}
                for s in stocks_sorted[:5]
            ],
            "losers": [
                {"symbol": s.get("symbol"), "percent": s.get("pChange")}
                for s in stocks_sorted[-5:]
            ],
        }

        cache_set("top_movers", response)
        return response

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# --------------------------------------------------
# 5️⃣ SINGLE STOCK DETAILS (SAFE)
# --------------------------------------------------
@router.get("/stock/{symbol}")
def stock_details(symbol: str):
    symbol_upper = symbol.upper()

    # 🚫 BLOCK INDEX SYMBOLS (VERY IMPORTANT)
    if any(k in symbol_upper for k in ["NIFTY", "SENSEX", "BANK", "MIDCAP", "SMALLCAP"]):
        raise HTTPException(
            status_code=400,
            detail="Index symbols are not supported for stock details",
        )

    try:
        session = create_session()
        res = session.get(
            f"{BASE_URL}/api/quote-equity?symbol={symbol_upper}",
            timeout=10,
        )

        data = res.json()
        p = data.get("priceInfo")
        if not p:
            raise Exception("Invalid stock detail response")

        return {
            "symbol": symbol_upper,
            "price": p.get("lastPrice"),
            "change": p.get("change"),
            "percent": p.get("pChange"),
            "open": p.get("open"),
            "high": p.get("intraDayHighLow", {}).get("max"),
            "low": p.get("intraDayHighLow", {}).get("min"),
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# --------------------------------------------------
# 6️⃣ HEALTH CHECK
# --------------------------------------------------
@router.get("/health")
def health():
    return {
        "status": "OK",
        "service": "Market Backend",
        "time": datetime.now(),
    }
