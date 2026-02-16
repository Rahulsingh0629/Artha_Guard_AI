from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from app.database.models import User
from app.auth.jwt_manager import get_current_user
from app.agents.advisory_engine.allocator import AssetAllocator
from app.agents.advisory_engine.scenario_simulator import ScenarioSimulator
from app.agents.advisory_engine.advisory_chat import AdvisoryAI
from app.agents.advisory_engine.profiler import UserProfiler

router = APIRouter()


def _safe_float(value, default=0.0):
    try:
        return float(value)
    except (TypeError, ValueError):
        return float(default)


def _percent_to_ratio(value: str) -> float:
    """
    Converts strings like "50%" to 0.50.
    """
    if not value:
        return 0.0
    cleaned = str(value).replace("%", "").strip()
    try:
        return float(cleaned) / 100.0
    except (TypeError, ValueError):
        return 0.0


def _build_allocation_amounts(allocation: dict, monthly_sip: float) -> dict:
    amounts = {}
    for key, value in allocation.items():
        if key == "Strategy":
            continue
        ratio = _percent_to_ratio(value)
        amounts[key] = {
            "weight": value,
            "monthly_amount": round(monthly_sip * ratio, 2)
        }
    return amounts

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
async def get_instant_advice(data: InstantAdviceRequest):
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
async def update_financial_profile(
    profile_data: UserProfileUpdate,
    current_user: User = Depends(get_current_user)
):
    # Update fields directly on the Beanie Document
    current_user.age = profile_data.age
    current_user.annual_income = profile_data.annual_income
    current_user.monthly_savings = profile_data.monthly_savings
    current_user.risk_appetite = profile_data.risk_appetite
    current_user.financial_goal = profile_data.financial_goal
    current_user.time_horizon_years = profile_data.time_horizon_years
    
    # Save to MongoDB
    await current_user.save()
    
    return {"status": "Profile updated successfully", "user": current_user.email}

@router.get("/plan")
async def get_investment_plan(
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
    stock_ideas = allocator.get_stock_recommendations(risk_profile["risk_category"])

    projection = simulator.simulate_wealth(
        current_investment=0, 
        monthly_sip=current_user.monthly_savings or 0,
        years=current_user.time_horizon_years or 10
    )

    monthly_sip = _safe_float(current_user.monthly_savings, 0)
    annual_income = _safe_float(current_user.annual_income, 0)
    yearly_investment = round(monthly_sip * 12, 2)
    savings_rate_pct = round((yearly_investment / annual_income) * 100, 2) if annual_income > 0 else 0.0

    detailed_allocation = _build_allocation_amounts(allocation, monthly_sip)
    risk_category = risk_profile.get("risk_category", "MODERATE")
    description = risk_profile.get("description", "")

    action_plan = [
        "Invest the monthly SIP within the first 5 trading days every month.",
        "Keep at least 3-6 months of expenses in emergency liquid funds before increasing equity risk.",
        "Rebalance portfolio every 6 months to restore target allocation weights.",
        "Review performance against goal every quarter and increase SIP by 5-10% yearly if possible."
    ]

    explanation = (
        f"Based on your age ({current_user.age}), savings pattern, and goal ({current_user.financial_goal}), "
        f"your profile is {risk_category}. {description} "
        f"With a monthly SIP of Rs. {round(monthly_sip, 2)}, the suggested allocation and stock ideas below "
        f"aim to balance growth and risk over {current_user.time_horizon_years or 10} years."
    )

    return {
        "status": "success",
        "user_profile": {
            "age": current_user.age,
            "goal": current_user.financial_goal,
            "annual_income": annual_income,
            "monthly_savings": monthly_sip,
            "time_horizon_years": current_user.time_horizon_years or 10,
            "savings_rate_percent": savings_rate_pct
        },
        "ai_analysis": risk_profile,
        "recommended_portfolio": allocation,
        "allocation_with_amounts": detailed_allocation,
        "stock_recommendations": stock_ideas,
        "advisory_explanation": explanation,
        "action_plan": action_plan,
        "wealth_projection": projection
    }

@router.post("/chat")
async def chat_with_advisor(
    request: AdvisoryChatRequest,
    current_user: User = Depends(get_current_user)
):
    try:
        bot = AdvisoryAI()

        user_context = {
            "risk_category": current_user.risk_appetite or "Unknown",
            "horizon": f"{current_user.time_horizon_years} years" if current_user.time_horizon_years else "Unknown"
        }

        response = bot.get_advice(
            request.message,
            user_profile=user_context,
            portfolio_summary="See investment plan",
        )
        return {"response": response}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Advisor service error: {str(e)}")
