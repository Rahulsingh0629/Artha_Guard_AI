from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from app.auth.jwt_manager import get_current_user
from app.database.models import AlertEvent, User, UserAlertPreference, UserPlan

router = APIRouter()
IST = timezone(timedelta(hours=5, minutes=30))


class AlertPreferenceUpdate(BaseModel):
    enabled: bool = True
    preferred_symbols: list[str] = Field(default_factory=list)
    daily_max_picks: int = 7
    min_profit_score: int = 40


@router.get("/latest")
async def get_latest_alerts(
    limit: int = 200,
    current_user: User = Depends(get_current_user),
):
    safe_limit = min(max(limit, 1), 1000)
    now_ist = datetime.now(IST)

    plan_value = (
        current_user.plan_type.value
        if hasattr(current_user.plan_type, "value")
        else str(current_user.plan_type)
    )
    is_free_plan = plan_value == UserPlan.FREE.value

    # Free users can view this only for the first 3 days of a month.
    if is_free_plan and now_ist.day > 3:
        return {
            "locked": True,
            "message": "Take a subscription to unlock this feature.",
            "alerts": [],
            "count": 0,
            "server_time_ist": now_ist.isoformat(),
            "timezone": "Asia/Kolkata",
        }

    day_start_ist = datetime(now_ist.year, now_ist.month, now_ist.day, tzinfo=IST)
    day_start_utc = day_start_ist.astimezone(timezone.utc).replace(tzinfo=None)

    alerts = (
        await AlertEvent.find(
            AlertEvent.user_email == current_user.email,
            AlertEvent.created_at >= day_start_utc,
        )
        .sort([("priority_score", -1), ("created_at", -1)])
        .limit(safe_limit)
        .to_list()
    )

    serialized = [
        {
            "symbol": item.symbol,
            "alert_type": item.alert_type,
            "priority_score": item.priority_score,
            "message": item.message,
            "created_at": item.created_at.isoformat() if item.created_at else None,
        }
        for item in alerts
    ]

    return {
        "locked": False,
        "message": "",
        "alerts": serialized,
        "count": len(serialized),
        "server_time_ist": now_ist.isoformat(),
        "timezone": "Asia/Kolkata",
    }


@router.get("/preferences")
async def get_alert_preferences(current_user: User = Depends(get_current_user)):
    prefs = await UserAlertPreference.find_one(
        UserAlertPreference.user_email == current_user.email
    )
    if not prefs:
        return {
            "enabled": True,
            "preferred_symbols": [],
            "daily_max_picks": 7,
            "min_profit_score": 40,
        }
    return {
        "enabled": prefs.enabled,
        "preferred_symbols": prefs.preferred_symbols,
        "daily_max_picks": prefs.daily_max_picks,
        "min_profit_score": prefs.min_profit_score,
    }


@router.put("/preferences")
async def update_alert_preferences(
    payload: AlertPreferenceUpdate,
    current_user: User = Depends(get_current_user),
):
    symbols = [s.strip().upper() for s in payload.preferred_symbols if s and s.strip()]
    daily_max = min(max(int(payload.daily_max_picks), 5), 7)
    min_score = min(max(int(payload.min_profit_score), 20), 90)

    prefs = await UserAlertPreference.find_one(
        UserAlertPreference.user_email == current_user.email
    )
    if not prefs:
        prefs = UserAlertPreference(
            user_email=current_user.email,
            enabled=payload.enabled,
            preferred_symbols=symbols,
            daily_max_picks=daily_max,
            min_profit_score=min_score,
        )
        await prefs.create()
    else:
        prefs.enabled = payload.enabled
        prefs.preferred_symbols = symbols
        prefs.daily_max_picks = daily_max
        prefs.min_profit_score = min_score
        await prefs.save()

    return {
        "status": "updated",
        "enabled": prefs.enabled,
        "preferred_symbols": prefs.preferred_symbols,
        "daily_max_picks": prefs.daily_max_picks,
        "min_profit_score": prefs.min_profit_score,
    }
