from fastapi import APIRouter, HTTPException, Query
import requests
import time
from datetime import datetime
import math

router = APIRouter()

BASE_URL = "https://www.nseindia.com"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
    "Accept": "application/json",
    "Accept-Language": "en-US,en;q=0.9",
    "Referer": "https://www.nseindia.com",
    "Connection": "keep-alive",
}

CACHE = {}
CACHE_TTL = 30 
HISTORY_CACHE_TTL = 20 * 60


def cache_get(key):
    if key in CACHE:
        data, ts = CACHE[key]
        if time.time() - ts < CACHE_TTL:
            return data
    return None


def cache_set(key, value):
    CACHE[key] = (value, time.time())


def cache_get_with_ttl(key, ttl: int):
    if key in CACHE:
        data, ts = CACHE[key]
        if time.time() - ts < ttl:
            return data
    return None


def get_stock_logo(symbol: str | None):
    if not symbol:
        return None
    return f"https://assets.tickertape.in/stocks/{symbol.upper()}.png"


def create_session():
    session = requests.Session()
    session.headers.update(HEADERS)

    home = session.get(BASE_URL, timeout=10)
    if home.status_code != 200:
        raise Exception("Failed to initialize NSE session")

    return session


INDEX_ALIASES = {
    "nifty": {
        "canonical": "NIFTY",
        "display_name": "NIFTY 50",
        "nse_index_name": "NIFTY 50",
        "yahoo_candidates": ["^NSEI"],
        "logo": None,
    },
    "nifty50": {
        "canonical": "NIFTY",
        "display_name": "NIFTY 50",
        "nse_index_name": "NIFTY 50",
        "yahoo_candidates": ["^NSEI"],
        "logo": None,
    },
    "sensex": {
        "canonical": "SENSEX",
        "display_name": "SENSEX",
        "nse_index_name": "SENSEX",
        "yahoo_candidates": ["^BSESN"],
        "logo": None,
    },
    "banknifty": {
        "canonical": "BANKNIFTY",
        "display_name": "NIFTY BANK",
        "nse_index_name": "NIFTY BANK",
        "yahoo_candidates": ["^NSEBANK"],
        "logo": None,
    },
    "finnifty": {
        "canonical": "FINNIFTY",
        "display_name": "NIFTY FIN SERVICE",
        "nse_index_name": "NIFTY FIN SERVICE",
        "yahoo_candidates": ["NIFTY_FIN_SERVICE.NS", "^CNXFINSERVICE"],
        "logo": None,
    },
    "midcap": {
        "canonical": "MIDCAP",
        "display_name": "NIFTY MIDCAP 50",
        "nse_index_name": "NIFTY MIDCAP 50",
        "yahoo_candidates": ["^NSEMDCP50", "NIFTY_MIDCAP_50.NS"],
        "logo": None,
    },
    "smallcap": {
        "canonical": "SMALLCAP",
        "display_name": "NIFTY SMALLCAP 50",
        "nse_index_name": "NIFTY SMALLCAP 50",
        "yahoo_candidates": ["^NSESMLCAP50", "NIFTY_SMALLCAP_50.NS"],
        "logo": None,
    },
}


def _normalize_symbol(raw_symbol: str) -> str:
    return (raw_symbol or "").strip().upper()


def _index_meta_from_symbol(symbol: str):
    key = symbol.lower().replace("^", "").replace("-", "").replace("_", "").replace(" ", "")
    return INDEX_ALIASES.get(key)


def _history_config(range_key: str):
    key = (range_key or "1D").upper()
    mapping = {
        "1D": {"period": "1d", "interval": "5m"},
        "1W": {"period": "5d", "interval": "15m"},
        "1M": {"period": "1mo", "interval": "1h"},
        "3M": {"period": "3mo", "interval": "1d"},
        "1Y": {"period": "1y", "interval": "1d"},
    }
    if key not in mapping:
        raise HTTPException(status_code=400, detail="Unsupported range. Use one of 1D, 1W, 1M, 3M, 1Y.")
    cfg = mapping[key]
    return key, cfg["period"], cfg["interval"]


def _safe_float(value):
    if value is None:
        return None
    try:
        f = float(value)
    except (TypeError, ValueError):
        return None
    if math.isnan(f) or math.isinf(f):
        return None
    return f


def _extract_chart_points(chart_payload: dict):
    timestamps = chart_payload.get("timestamp") or []
    indicators = chart_payload.get("indicators") or {}
    quote_entries = indicators.get("quote") or []
    quote = quote_entries[0] if quote_entries else {}

    opens = quote.get("open") or []
    highs = quote.get("high") or []
    lows = quote.get("low") or []
    closes = quote.get("close") or []
    volumes = quote.get("volume") or []

    points = []
    for idx, ts in enumerate(timestamps):
        close = _safe_float(closes[idx] if idx < len(closes) else None)
        if close is None:
            continue

        points.append({
            "timestamp": datetime.utcfromtimestamp(ts).isoformat() + "Z",
            "open": _safe_float(opens[idx] if idx < len(opens) else None),
            "high": _safe_float(highs[idx] if idx < len(highs) else None),
            "low": _safe_float(lows[idx] if idx < len(lows) else None),
            "close": close,
            "volume": _safe_float(volumes[idx] if idx < len(volumes) else None),
        })

    return points


def _fetch_yahoo_chart(symbol_candidates: list[str], period: str, interval: str):
    last_error = None
    for candidate in symbol_candidates:
        try:
            res = requests.get(
                f"https://query1.finance.yahoo.com/v8/finance/chart/{candidate}",
                params={
                    "range": period,
                    "interval": interval,
                    "includePrePost": "false",
                    "events": "div,splits",
                },
                headers={
                    "User-Agent": HEADERS["User-Agent"],
                    "Accept": "application/json",
                },
                timeout=12,
            )
            data = res.json()
            result = data.get("chart", {}).get("result") or []
            if not result:
                continue

            chart_payload = result[0]
            points = _extract_chart_points(chart_payload)
            if points:
                return candidate, chart_payload, points
        except Exception as exc:
            last_error = exc
            continue

    if last_error:
        raise Exception(f"Unable to fetch market history ({last_error})")
    raise Exception("Unable to fetch market history for symbol")


def _fetch_yfinance_history(symbol_candidates: list[str], period: str, interval: str):
    """
    Backward-compatible helper name (now powered by Yahoo chart API via requests).
    """
    return _fetch_yahoo_chart(symbol_candidates=symbol_candidates, period=period, interval=interval)


def _resolve_instrument(symbol: str):
    normalized = _normalize_symbol(symbol)
    index_meta = _index_meta_from_symbol(normalized)
    if index_meta:
        return {
            "symbol": index_meta["canonical"],
            "display_name": index_meta["display_name"],
            "instrument_type": "index",
            "nse_symbol": None,
            "nse_index_name": index_meta["nse_index_name"],
            "yahoo_candidates": index_meta["yahoo_candidates"],
            "logo": index_meta["logo"],
        }

    return {
        "symbol": normalized,
        "display_name": normalized,
        "instrument_type": "stock",
        "nse_symbol": normalized,
        "nse_index_name": None,
        "yahoo_candidates": [normalized, f"{normalized}.NS", f"{normalized}.BO"],
        "logo": get_stock_logo(normalized),
    }


def _instrument_details_from_nse(meta: dict):
    if meta["instrument_type"] == "index":
        session = create_session()
        res = session.get(f"{BASE_URL}/api/allIndices", timeout=10)
        payload = res.json()
        items = payload.get("data")
        if not isinstance(items, list):
            raise Exception("Invalid indices response")
        for entry in items:
            if entry.get("index") == meta["nse_index_name"]:
                return {
                    "symbol": meta["symbol"],
                    "name": meta["display_name"],
                    "instrumentType": "index",
                    "price": _safe_float(entry.get("last")),
                    "change": _safe_float(entry.get("change")),
                    "percent": _safe_float(entry.get("percentChange")),
                    "open": _safe_float(entry.get("open")),
                    "high": _safe_float(entry.get("high")),
                    "low": _safe_float(entry.get("low")),
                    "previousClose": _safe_float(entry.get("previousClose")),
                    "logo": meta["logo"],
                }
        raise Exception(f"Index details not found for {meta['display_name']}")

    session = create_session()
    res = session.get(
        f"{BASE_URL}/api/quote-equity?symbol={meta['nse_symbol']}",
        timeout=10,
    )
    data = res.json()
    p = data.get("priceInfo")
    if not p:
        raise Exception("Invalid stock detail response")

    return {
        "symbol": meta["symbol"],
        "name": data.get("info", {}).get("companyName") or meta["display_name"],
        "instrumentType": "stock",
        "price": _safe_float(p.get("lastPrice")),
        "change": _safe_float(p.get("change")),
        "percent": _safe_float(p.get("pChange")),
        "open": _safe_float(p.get("open")),
        "high": _safe_float(p.get("intraDayHighLow", {}).get("max")),
        "low": _safe_float(p.get("intraDayHighLow", {}).get("min")),
        "previousClose": _safe_float(p.get("previousClose")),
        "logo": meta["logo"],
    }


def _instrument_details_from_yfinance(meta: dict):
    used_symbol, chart_payload, points = _fetch_yfinance_history(
        symbol_candidates=meta["yahoo_candidates"],
        period="5d",
        interval="1d",
    )

    if not points:
        raise Exception("No Yahoo detail points available")

    last = points[-1]
    prev = points[-2]["close"] if len(points) > 1 else _safe_float(
        (chart_payload.get("meta") or {}).get("chartPreviousClose")
    )
    close = last["close"]
    change = None
    percent = None
    if close is not None and prev is not None:
        change = close - prev
        percent = (change / prev) * 100 if prev != 0 else None

    meta_info = chart_payload.get("meta") or {}
    resolved_name = meta_info.get("symbol") or meta["display_name"]

    return {
        "symbol": meta["symbol"],
        "name": resolved_name if meta["instrument_type"] == "stock" else meta["display_name"],
        "instrumentType": meta["instrument_type"],
        "price": close,
        "change": _safe_float(change),
        "percent": _safe_float(percent),
        "open": last["open"],
        "high": last["high"],
        "low": last["low"],
        "previousClose": prev,
        "logo": meta["logo"] if meta["instrument_type"] == "stock" else None,
        "source": f"yahoo:{used_symbol}",
    }

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
            symbol = s.get("symbol")
            result.append({
                "symbol": symbol,
                "name": s.get("meta", {}).get("companyName", symbol),
                "price": s.get("lastPrice"),
                "change": s.get("change"),
                "percent": s.get("pChange"),
                "open": s.get("open"),
                "high": s.get("dayHigh"),
                "low": s.get("dayLow"),
                "previousClose": s.get("previousClose"),
                "logo": get_stock_logo(symbol),
            })

        response = {"count": len(result), "stocks": result}
        cache_set("stocks", response)
        return response

    except Exception as e:
        print("🔥 STOCKS ERROR:", e)
        raise HTTPException(status_code=500, detail=str(e))


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
                {
                    "symbol": s.get("symbol"),
                    "percent": s.get("pChange"),
                    "logo": get_stock_logo(s.get("symbol")),
                }
                for s in stocks_sorted if s.get("pChange", 0) > 0
            ],
            "losers": [
                {
                    "symbol": s.get("symbol"),
                    "percent": s.get("pChange"),
                    "logo": get_stock_logo(s.get("symbol")),
                }
                for s in stocks_sorted if s.get("pChange", 0) < 0
            ],
        }

        cache_set("top_movers", response)
        return response

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/instrument/{symbol}")
def instrument_details(symbol: str):
    """
    Unified details endpoint for both stocks and indices.
    """
    meta = _resolve_instrument(symbol)
    cache_key = f"instrument_details:{meta['symbol']}"
    cached = cache_get(cache_key)
    if cached:
        return cached

    try:
        details = _instrument_details_from_nse(meta)
        cache_set(cache_key, details)
        return details
    except Exception:
        # Fallback to yfinance if NSE payload is unavailable.
        try:
            details = _instrument_details_from_yfinance(meta)
            cache_set(cache_key, details)
            return details
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))


@router.get("/instrument/{symbol}/history")
def instrument_history(
    symbol: str,
    range: str = Query(default="1D", description="1D, 1W, 1M, 3M, 1Y"),
):
    """
    Real historical candles for stocks and indices.
    """
    meta = _resolve_instrument(symbol)
    range_key, period, interval = _history_config(range)
    cache_key = f"instrument_history:{meta['symbol']}:{range_key}:{interval}"
    cached = cache_get_with_ttl(cache_key, HISTORY_CACHE_TTL)
    if cached:
        return cached

    try:
        used_symbol, _chart_payload, points = _fetch_yfinance_history(
            symbol_candidates=meta["yahoo_candidates"],
            period=period,
            interval=interval,
        )

        if not points:
            raise Exception("No historical data available for this symbol")

        close_values = [p["close"] for p in points if p["close"] is not None]
        low = min(close_values) if close_values else None
        high = max(close_values) if close_values else None

        response = {
            "symbol": meta["symbol"],
            "name": meta["display_name"],
            "instrumentType": meta["instrument_type"],
            "range": range_key,
            "interval": interval,
            "source": f"yahoo:{used_symbol}",
            "points": points,
            "summary": {
                "count": len(points),
                "firstClose": close_values[0] if close_values else None,
                "lastClose": close_values[-1] if close_values else None,
                "highClose": _safe_float(high),
                "lowClose": _safe_float(low),
            },
        }

        cache_set(cache_key, response)
        return response
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/stock/{symbol}/history")
def stock_history_alias(
    symbol: str,
    range: str = Query(default="1D", description="1D, 1W, 1M, 3M, 1Y"),
):
    """
    Backward-compatible alias used by older clients.
    """
    return instrument_history(symbol=symbol, range=range)


@router.get("/stock/{symbol}")
def stock_details(symbol: str):
    # Backward compatibility: delegate to unified instrument details.
    return instrument_details(symbol=symbol)


@router.get("/health")
def health():
    return {
        "status": "OK",
        "service": "Market Backend",
        "time": datetime.now(),
    }
