from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from typing import cast 
from app.database.models import User, UserActivityLog, UserPlan
from app.subscription.plan_checker import PLAN_CONFIG, FeatureName

class AccessDeniedError(Exception):
    """Custom exception when a user is blocked."""
    pass

class FeatureGuard:
    @staticmethod
    def check_access(db: Session, user: User, feature: FeatureName):
        """
        Main gatekeeper function.
        Returns TRUE if allowed, raises AccessDeniedError if blocked.
        """
        
        # 1. Get Plan Value safely (Handle both Enum object and String)
        # SQLAlchemy returns the Enum object (UserPlan.FREE), but sometimes it might be a string.
        if hasattr(user.plan_type, "value"):
            user_plan_value = user.plan_type.value  # e.g., "pro"
        else:
            user_plan_value = str(user.plan_type)

        # 2. ELITE users skip all checks (God mode)
        # We compare value-to-value
        if user_plan_value == UserPlan.ELITE.value:
            return True

        # 3. Get Rules for the plan
        rules = PLAN_CONFIG.get(user_plan_value, PLAN_CONFIG["free"])

        # 4. Check if feature is completely allowed for this plan
        if feature not in rules["allowed_features"]:
             raise AccessDeniedError(
                f"Upgrade to PRO to access {feature.value}"
            )

        # 5. Check Usage Limits
        limit = rules["limits"].get(feature)
        if limit:
            # FIX: Use 'cast' to tell Pylance this is definitely an integer
            user_id_int = cast(int, user.id) 
            
            usage_count = FeatureGuard._get_monthly_usage(db, user_id_int, feature)
            
            if usage_count >= limit:
                raise AccessDeniedError(
                    f"Monthly limit reached ({usage_count}/{limit}). Upgrade to increase limits."
                )

        return True

    @staticmethod
    def log_usage(db: Session, user_id: int, feature: FeatureName):
        """
        Call this AFTER a feature is successfully used.
        """
        log = UserActivityLog(
            user_id=user_id,
            action_type=feature.value,
            timestamp=datetime.utcnow()
        )
        db.add(log)
        db.commit()

    @staticmethod
    def _get_monthly_usage(db: Session, user_id: int, feature: FeatureName) -> int:
        """Counts usage in the last 30 days."""
        thirty_days_ago = datetime.utcnow() - timedelta(days=30)
        
        return db.query(UserActivityLog).filter(
            UserActivityLog.user_id == user_id,
            UserActivityLog.action_type == feature.value,
            UserActivityLog.timestamp >= thirty_days_ago
        ).count()