from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional

from app.database.session import get_db
from app.database.models import User
from app.auth.jwt_manager import get_current_user

# Import your custom engines
from app.agents.advisory_engine.allocator import AssetAllocator
from app.agents.advisory_engine.scenario_simulator import ScenarioSimulator
from app.agents.advisory_engine.advisory_chat import AdvisoryAI
from app.agents.advisory_engine.profiler import UserProfiler

router = APIRouter()

# --- INPUT MODELS ---
class AdvisoryChatRequest(BaseModel):
    message: str

class UserProfileUpdate(BaseModel):
    age: int
    annual_income: float
    monthly_savings: float
    risk_appetite: str  
    financial_goal: str
    time_horizon_years: int

# [NEW] Model for Instant Advice (User Data + Question together)
class InstantAdviceRequest(BaseModel):
    age: int
    annual_income: float
    monthly_savings: float
    financial_goal: str
    time_horizon_years: int
    question: str

# --- 1. INSTANT ADVICE ENDPOINT (NEW) ---
@router.post("/instant_advice")
def get_instant_advice(data: InstantAdviceRequest):
    """
    Takes user data + question, analyzes risk, calculates allocation, 
    and returns an AI answer immediately.
    """
    try:
        # 1. Initialize Engines
        profiler = UserProfiler()
        allocator = AssetAllocator()
        bot = AdvisoryAI()

        # 2. Calculate Savings Rate (Required by Profiler)
        # Formula: (Monthly * 12) / Annual Income
        if data.annual_income > 0:
            savings_rate = (data.monthly_savings * 12) / data.annual_income
        else:
            savings_rate = 0

        # 3. Determine Risk Profile
        # Note: We pass 0.0 as savings_rate if calculation fails
        risk_result = profiler.analyze_profile(
            age=data.age, 
            income=data.annual_income, 
            savings_rate=savings_rate
        )

        # 4. Get Asset Allocation based on that Risk
        portfolio_split = allocator.get_suggested_allocation(risk_result["risk_category"])

        # 5. Get AI Response
        # We pass the profile and the calculated portfolio to the AI
        ai_response = bot.get_advice(
            user_query=data.question,
            user_profile={
                "risk_category": risk_result["risk_category"], 
                "horizon": f"{data.time_horizon_years} years",
                "goal": data.financial_goal
            },
            portfolio_summary=str(portfolio_split)
        )

        return {
            "status": "success",
            "analysis": {
                "risk_profile": risk_result["risk_category"],
                "suggested_portfolio": portfolio_split
            },
            "ai_advice": ai_response
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating advice: {str(e)}")


# --- 2. UPDATE PROFILE (Existing) ---
@router.post("/update_profile")
def update_financial_profile(
    profile_data: UserProfileUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    current_user.age = profile_data.age
    current_user.annual_income = profile_data.annual_income
    current_user.monthly_savings = profile_data.monthly_savings
    current_user.risk_appetite = profile_data.risk_appetite
    current_user.financial_goal = profile_data.financial_goal
    current_user.time_horizon_years = profile_data.time_horizon_years
    
    db.commit()
    return {"status": "Profile updated successfully", "user": current_user.email}

# --- 3. GET INVESTMENT PLAN (Existing) ---
@router.get("/plan")
def get_investment_plan(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    if not current_user.age or not current_user.annual_income:
        raise HTTPException(status_code=400, detail="Please update your profile first using /update_profile")

    profiler = UserProfiler()
    allocator = AssetAllocator()
    simulator = ScenarioSimulator()

    # Calculate Savings Rate
    savings_rate = 0
    if current_user.annual_income > 0:
        savings_rate = (current_user.monthly_savings * 12) / current_user.annual_income

    # Calculate Risk Score
    risk_profile = profiler.analyze_profile(
        age=current_user.age,
        income=current_user.annual_income,
        savings_rate=savings_rate
    )

    # Generate Asset Allocation
    allocation = allocator.get_suggested_allocation(risk_profile['risk_category'])

    # Simulate Future Wealth
    projection = simulator.simulate_wealth(
        current_investment=0, # Assuming 0 start for simplicity in this view
        monthly_sip=current_user.monthly_savings,
        years=current_user.time_horizon_years or 10
    )

    return {
        "user_profile": {
            "age": current_user.age,
            "goal": current_user.financial_goal
        },
        "ai_analysis": risk_profile,
        "recommended_portfolio": allocation,
        "wealth_projection": projection
    }

# --- 4. CHAT WITH ADVISOR (Existing) ---
@router.post("/chat")
def chat_with_advisor(
    request: AdvisoryChatRequest,
    current_user: User = Depends(get_current_user)
):
    bot = AdvisoryAI()
    
    # Construct a simple profile dict from DB user
    user_context = {
        "risk_category": current_user.risk_appetite or "Unknown",
        "horizon": f"{current_user.time_horizon_years} years" if current_user.time_horizon_years else "Unknown"
    }
    
    response = bot.get_advice(request.message, user_profile=user_context, portfolio_summary="See investment plan")
    return {"response": response}