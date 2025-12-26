import os
from motor.motor_asyncio import AsyncIOMotorClient
from beanie import init_beanie
from app.database.models import User

async def init_db():
    # 1. Get the URL
    mongo_url = os.getenv("MONGO_URL")
    
    # 2. Create Client
    client = AsyncIOMotorClient(mongo_url)
    
    # 3. Initialize Beanie
    # FIX: Add '# type: ignore' to silence the Pylance error
    await init_beanie(database=client.arthaguard_db, document_models=[User])  # type: ignore