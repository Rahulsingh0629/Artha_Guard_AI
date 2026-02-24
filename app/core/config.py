import os
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    PROJECT_NAME: str = "ArthaGuard AI"
    VERSION: str = "1.0.0"
    
    # Security
    SECRET_KEY: str = os.getenv("SECRET_KEY", "super_secret_key_for_jwt") 
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 10080
    
    # Database
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///./arthaguard.db") 
    MONGO_URL: str = os.getenv("MONGO_URL", "")

    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")

    # External APIs
    NSE_API_KEY: str = os.getenv("NSE_API_KEY", "")
    NEWS_API_KEY: str = os.getenv("NEWS_API_KEY", "")

    # 👇 ADD THIS LINE TO FIX THE ERROR
    ALPHA_VANTAGE_API_KEY: str = os.getenv("ALPHA_VANTAGE_API_KEY", "") 

    # Twilio Settings
    TWILIO_SID: str = ""
    TWILIO_AUTH_TOKEN: str = ""
    TWILIO_PHONE_NUMBER: str = ""

    # Email Settings
    SMTP_SERVER: str = "smtp.gmail.com"
    SMTP_PORT: int = 587
    EMAIL_SENDER: str = ""
    EMAIL_PASSWORD: str = ""

    class Config:
        env_file = ".env"
        # Optional: Add this to ignore other unknown variables in .env instead of crashing
        extra = "ignore" 

settings = Settings()