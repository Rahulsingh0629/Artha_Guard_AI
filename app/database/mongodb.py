import os
from motor.motor_asyncio import AsyncIOMotorClient
from beanie import init_beanie

# Import ALL your models here
from app.database.models import (
    User, 
    Portfolio, 
    UserActivityLog, 
    TipCheckHistory, 
    AlertConfig, 
    OTPVerification
)

async def init_db():
    mongo_url = os.getenv("MONGO_URL")
    
    if not mongo_url:
        print("❌ Error: MONGO_URL not found in .env file!")
        return

    client = AsyncIOMotorClient(mongo_url)
    
    # FIX: Add '# type: ignore' at the end of this line to silence the error
    await init_beanie(
        database=client.arthaguard_db,  # type: ignore
        document_models=[
            User,
            Portfolio,
            UserActivityLog,
            TipCheckHistory,
            AlertConfig,
            OTPVerification
        ]
    )
    print("✅ Database Initialized with all models.")