import os
import httpx
from fastapi import APIRouter

router = APIRouter()

API_KEY = os.getenv("ALPHA_VANTAGE_API_KEY")
BASE_URL = "https://www.alphavantage.co/query"


@router.get("/indices")
async def get_indices():
    async with httpx.AsyncClient() as client:
        nifty = await client.get(BASE_URL, params={
            "function": "GLOBAL_QUOTE",
            "symbol": "^NSEI",
            "apikey": API_KEY
        })

        sensex = await client.get(BASE_URL, params={
            "function": "GLOBAL_QUOTE",
            "symbol": "^BSESN",
            "apikey": API_KEY
        })

    return {
        "nifty": nifty.json(),
        "sensex": sensex.json()
    }
