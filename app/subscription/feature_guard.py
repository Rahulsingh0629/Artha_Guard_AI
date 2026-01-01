from datetime import datetime, timedelta
from app.database.models import User, UserActivityLog, UserPlan
from app.subscription.plan_checker import PLAN_CONFIG, FeatureName

class AccessDeniedError(Exception):
    """Custom exception when a user is blocked."""
    pass

class FeatureGuard:
    @staticmethod
    async def check_access(user: User, feature: FeatureName) -> bool:
        """
        Async Gatekeeper for MongoDB.
        Returns TRUE if allowed, raises AccessDeniedError if blocked.
        """
        
        # 1. Get Plan Value safely
        plan_value = user.plan_type.value if hasattr(user.plan_type, "value") else str(user.plan_type)

        # 2. ELITE users skip checks
        if plan_value == UserPlan.ELITE.value:
            return True

        # 3. Get Rules
        rules = PLAN_CONFIG.get(plan_value, PLAN_CONFIG["free"])

        # 4. Check Permission
        if feature not in rules["allowed_features"]:
             raise AccessDeniedError(f"Upgrade to PRO to access {feature.value}")

        # 5. Check Usage Limits (Async Count)
        limit = rules["limits"].get(feature)
        if limit:
            usage_count = await FeatureGuard._get_monthly_usage(user.email, feature)
            
            if usage_count >= limit:
                raise AccessDeniedError(
                    f"Monthly limit reached ({usage_count}/{limit}). Upgrade to increase limits."
                )

        return True

    @staticmethod
    async def log_usage(user_email: str, feature: FeatureName):
        """
        Async Logger: Saves activity to MongoDB.
        """
        log = UserActivityLog(
            user_email=user_email,
            action_type=feature.value,
            timestamp=datetime.utcnow()
        )
        await log.create()

    @staticmethod
    async def _get_monthly_usage(user_email: str, feature: FeatureName) -> int:
        """Counts usage in the last 30 days using Beanie."""
        thirty_days_ago = datetime.utcnow() - timedelta(days=30)
        
        # Beanie Query
        count = await UserActivityLog.find(
            UserActivityLog.user_email == user_email,
            UserActivityLog.action_type == feature.value,
            UserActivityLog.timestamp >= thirty_days_ago
        ).count()
        
        return count