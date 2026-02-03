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
    "Referer": "https://www.nseindia.com"
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
# NSE SESSION (ANTI-BLOCK)
# --------------------------------------------------
def create_session():
    session = requests.Session()
    session.get(BASE_URL, headers=HEADERS, timeout=5)
    return session


# --------------------------------------------------
# 1️⃣ MARKET STATUS
# --------------------------------------------------
@router.get("/market-status")
def market_status():
    now = datetime.now()
    weekday = now.weekday()  # 0 = Monday

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
        res = session.get(f"{BASE_URL}/api/allIndices", headers=HEADERS)
        data = res.json()["data"]

        REQUIRED = {
            "NIFTY 50": "nifty",
            "SENSEX": "sensex",
            "NIFTY BANK": "bankNifty",
            "NIFTY FIN SERVICE": "finNifty",
            "NIFTY MIDCAP 50": "midcap",
            "NIFTY SMALLCAP 50": "smallcap"
        }

        result = {}

        for i in data:
            if i["index"] in REQUIRED:
                key = REQUIRED[i["index"]]
                result[key] = {
                    "name": i["index"],
                    "price": i["last"],
                    "change": i["change"],
                    "percent": i["percentChange"]
                }

        cache_set("indices", result)
        return result

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# --------------------------------------------------
# 3️⃣ ALL NIFTY-50 STOCKS (LIVE)
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
            headers=HEADERS
        )

        stocks = res.json()["data"]
        result = []

        for s in stocks:
            result.append({
                "symbol": s["symbol"],
                "name": s["meta"]["companyName"],
                "price": s["lastPrice"],
                "change": s["change"],
                "percent": s["pChange"],
                "open": s["open"],
                "high": s["dayHigh"],
                "low": s["dayLow"],
                "previousClose": s["previousClose"]
            })

        response = {"count": len(result), "stocks": result}
        cache_set("stocks", response)
        return response

    except Exception as e:
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
            headers=HEADERS
        )

        stocks = res.json()["data"]
        stocks_sorted = sorted(stocks, key=lambda x: x["pChange"], reverse=True)

        gainers = stocks_sorted[:5]
        losers = stocks_sorted[-5:]

        response = {
            "gainers": [
                {"symbol": g["symbol"], "percent": g["pChange"]}
                for g in gainers
            ],
            "losers": [
                {"symbol": l["symbol"], "percent": l["pChange"]}
                for l in losers
            ]
        }

        cache_set("top_movers", response)
        return response

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# --------------------------------------------------
# 5️⃣ SINGLE STOCK DETAILS
# --------------------------------------------------
@router.get("/stock/{symbol}")
def stock_details(symbol: str):
    try:
        session = create_session()
        res = session.get(
            f"{BASE_URL}/api/quote-equity?symbol={symbol}",
            headers=HEADERS
        )

        p = res.json()["priceInfo"]

        return {
            "symbol": symbol,
            "price": p["lastPrice"],
            "change": p["change"],
            "percent": p["pChange"],
            "open": p["open"],
            "high": p["intraDayHighLow"]["max"],
            "low": p["intraDayHighLow"]["min"]
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
        "time": datetime.now()
    }
