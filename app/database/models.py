from typing import Optional
from beanie import Document
from pydantic import BaseModel, Field
from datetime import datetime
import enum

# --- ENUMS (Same as before) ---
class UserPlan(str, enum.Enum):
    FREE = "free"
    PRO = "pro"
    ELITE = "elite"

class RiskLevel(str, enum.Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    SCAM = "scam"

# --- USER MODEL ---
class User(Document):
    email: str 
    full_name: Optional[str] = None
    phone_number: Optional[str] = None
    hashed_password: str
    
    plan_type: UserPlan = UserPlan.FREE
    is_active: bool = True
    created_at: datetime = Field(default_factory=datetime.utcnow)

    # --- ADVISORY PROFILE (Stored directly inside the User document) ---
    age: Optional[int] = None
    annual_income: Optional[float] = None
    monthly_savings: Optional[float] = None
    risk_appetite: Optional[str] = None
    financial_goal: Optional[str] = None
    time_horizon_years: Optional[int] = None

    class Settings:
        name = "users" # Collection Name
        indexes = ["email", "phone_number"] # Make these searchable/unique

# --- PORTFOLIO MODEL ---
class Portfolio(Document):
    user_email: str  # We use email to link to the User
    stock_symbol: str
    quantity: int = 0
    average_buy_price: float = 0.0
    sector: Optional[str] = None

    created_at: datetime = Field(default_factory=datetime.utcnow)

    class Settings:
        name = "portfolios"

# --- ACTIVITY LOGS ---
class UserActivityLog(Document):
    user_email: str
    action_type: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)

    class Settings:
        name = "activity_logs"

# --- FAKE TIP CHECK HISTORY ---
class TipCheckHistory(Document):
    user_email: str
    tip_text_raw: str
    detected_stock: str
    credibility_score: float
    verdict: RiskLevel
    checked_at: datetime = Field(default_factory=datetime.utcnow)

    class Settings:
        name = "tip_check_history"

# --- ALERT CONFIG ---
class AlertConfig(Document):
    user_email: str
    stock_symbol: str
    target_price: float
    condition: str # e.g., "ABOVE", "BELOW"
    is_active: bool = True

    class Settings:
        name = "alert_configs"