from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional
from app.database.session import get_db
from app.database.models import User
from app.auth.jwt_manager import get_current_user
from app.agents.advisory_engine.allocator import AssetAllocator
from app.agents.advisory_engine.scenario_simulator import ScenarioSimulator
from app.agents.advisory_engine.advisory_chat import AdvisoryAI
from app.agents.advisory_engine.profiler import UserProfiler

router = APIRouter()

class AdvisoryChatRequest(BaseModel):
    message: str

class UserProfileUpdate(BaseModel):
    age: int
    annual_income: float
    monthly_savings: float
    risk_appetite: str  
    financial_goal: str
    time_horizon_years: int

class InstantAdviceRequest(BaseModel):
    age: int
    annual_income: float
    monthly_savings: float
    financial_goal: str
    time_horizon_years: int
    question: str

@router.post("/instant_advice")
def get_instant_advice(data: InstantAdviceRequest):
    
    try:
        profiler = UserProfiler()
        allocator = AssetAllocator()
        bot = AdvisoryAI()

        if data.annual_income > 0:
            savings_rate = (data.monthly_savings * 12) / data.annual_income
        else:
            savings_rate = 0

        risk_result = profiler.analyze_profile(
            age=data.age, 
            income=data.annual_income, 
            savings_rate=savings_rate
        )

        portfolio_split = allocator.get_suggested_allocation(risk_result["risk_category"])

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

    savings_rate = 0
    if current_user.annual_income and current_user.annual_income > 0 and current_user.monthly_savings:
        savings_rate = (current_user.monthly_savings * 12) / current_user.annual_income

    risk_profile = profiler.analyze_profile(
        age=current_user.age,
        income=current_user.annual_income,
        savings_rate=savings_rate
    )

    allocation = allocator.get_suggested_allocation(risk_profile['risk_category'])

    projection = simulator.simulate_wealth(
        current_investment=0, 
        monthly_sip=current_user.monthly_savings or 0,
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

@router.post("/chat")
def chat_with_advisor(
    request: AdvisoryChatRequest,
    current_user: User = Depends(get_current_user)
):
    bot = AdvisoryAI()
    
    user_context = {
        "risk_category": current_user.risk_appetite or "Unknown",
        "horizon": f"{current_user.time_horizon_years} years" if current_user.time_horizon_years else "Unknown"
    }
    
    response = bot.get_advice(request.message, user_profile=user_context, portfolio_summary="See investment plan")
    return {"response": response}