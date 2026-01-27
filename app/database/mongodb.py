import os
from motor.motor_asyncio import AsyncIOMotorClient
from beanie import init_beanie

from app.database.models import (
    User, 
    Portfolio, 
    UserActivityLog, 
    TipCheckHistory, 
    AlertConfig, 
)

async def init_db():
    mongo_url = os.getenv("MONGO_URL")
    
    if not mongo_url:
        print("❌ Error: MONGO_URL not found in .env file!")
        return

    client = AsyncIOMotorClient(mongo_url)
    
    await init_beanie(
        database=client.arthaguard_db,  # type: ignore
        document_models=[
            User,
            Portfolio,
            UserActivityLog,
            TipCheckHistory,
            AlertConfig,
        ]
    )
    print("✅ Database Initialized with all models.")