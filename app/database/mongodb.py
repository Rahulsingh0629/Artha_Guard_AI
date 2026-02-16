import os
from motor.motor_asyncio import AsyncIOMotorClient
from beanie import init_beanie
from dotenv import load_dotenv

from app.database.models import (
    User,
    Portfolio,
    UserActivityLog,
    TipCheckHistory,
    AlertConfig,
    AlertEvent,
    UserAlertPreference,
    UserScannerWatchlist,
)

load_dotenv(dotenv_path=".env")


async def init_db():
    mongo_url = os.getenv("MONGO_URL")

    if not mongo_url:
        raise RuntimeError("MONGO_URL not found. Add it in .env or environment variables.")

    client = AsyncIOMotorClient(mongo_url)

    await init_beanie(
        database=client.arthaguard_db,  # type: ignore
        document_models=[
            User,
            Portfolio,
            UserActivityLog,
            TipCheckHistory,
            AlertConfig,
            AlertEvent,
            UserAlertPreference,
            UserScannerWatchlist,
        ],
    )
    print("Database initialized with all models.")
