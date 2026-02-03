from fastapi import APIRouter, HTTPException
import requests

router = APIRouter()

BASE_URL = "https://www.nseindia.com"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
    "Accept": "application/json",
    "Accept-Language": "en-US,en;q=0.9",
    "Referer": "https://www.nseindia.com"
}


# --------------------------------------------------
# Create NSE-safe session
# --------------------------------------------------
def create_session():
    session = requests.Session()
    session.get(BASE_URL, headers=HEADERS, timeout=5)
    return session


# --------------------------------------------------
# 1️⃣ ALL MAJOR INDICES (NIFTY, SENSEX, BANKNIFTY…)
# --------------------------------------------------
@router.get("/indices")
def get_indices():
    try:
        session = create_session()
        response = session.get(
            f"{BASE_URL}/api/allIndices",
            headers=HEADERS,
            timeout=5
        )

        data = response.json()["data"]

        REQUIRED_INDICES = {
            "NIFTY 50": "nifty",
            "SENSEX": "sensex",
            "NIFTY BANK": "bankNifty",
            "NIFTY FIN SERVICE": "finNifty",
            "NIFTY MIDCAP 50": "midcap",
            "NIFTY SMALLCAP 50": "smallcap"
        }

        result = {}

        for index in data:
            if index["index"] in REQUIRED_INDICES:
                key = REQUIRED_INDICES[index["index"]]
                result[key] = {
                    "name": index["index"],
                    "price": index["last"],
                    "change": index["change"],
                    "percent": index["percentChange"]
                }

        return result

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# --------------------------------------------------
# 2️⃣ ALL NIFTY-50 STOCKS (LIVE)
# --------------------------------------------------
@router.get("/stocks")
def get_all_stocks():
    try:
        session = create_session()
        response = session.get(
            f"{BASE_URL}/api/equity-stockIndices?index=NIFTY%2050",
            headers=HEADERS,
            timeout=5
        )

        stocks = response.json()["data"]

        result = []

        for stock in stocks:
            result.append({
                "symbol": stock["symbol"],
                "name": stock["meta"]["companyName"],
                "price": stock["lastPrice"],
                "change": stock["change"],
                "percent": stock["pChange"],
                "open": stock["open"],
                "high": stock["dayHigh"],
                "low": stock["dayLow"],
                "previousClose": stock["previousClose"]
            })

        return {
            "count": len(result),
            "stocks": result
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# --------------------------------------------------
# 3️⃣ SINGLE STOCK DETAILS (ANY NSE STOCK)
# --------------------------------------------------
@router.get("/stock/{symbol}")
def get_stock(symbol: str):
    try:
        session = create_session()
        response = session.get(
            f"{BASE_URL}/api/quote-equity?symbol={symbol}",
            headers=HEADERS,
            timeout=5
        )

        data = response.json()["priceInfo"]

        return {
            "symbol": symbol,
            "price": data["lastPrice"],
            "change": data["change"],
            "percent": data["pChange"],
            "open": data["open"],
            "high": data["intraDayHighLow"]["max"],
            "low": data["intraDayHighLow"]["min"]
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
