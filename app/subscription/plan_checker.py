from enum import Enum

# Define Feature Names for consistency
class FeatureName(str, Enum):
    FAKE_TIP_CHECK = "fake_tip_check"
    PORTFOLIO_AI = "portfolio_ai"
    INTRADAY_SCANNER = "intraday_scanner"
    NEWS_ALERTS = "news_alerts"
    ADVISORY = "advisory"

# Define Plan Limits & Access
PLAN_CONFIG = {
    "free": {
        "allowed_features": [FeatureName.FAKE_TIP_CHECK], # Basic access
        "limits": {
            FeatureName.FAKE_TIP_CHECK: 3,  # Max 3 checks per month
            FeatureName.INTRADAY_SCANNER: 0, # No access
        }
    },
    "pro": {
        "allowed_features": [
            FeatureName.FAKE_TIP_CHECK, 
            FeatureName.INTRADAY_SCANNER, 
            FeatureName.NEWS_ALERTS
        ],
        "limits": {
            FeatureName.FAKE_TIP_CHECK: 1000, # Effectively unlimited
            FeatureName.INTRADAY_SCANNER: 1000
        }
    },
    "elite": {
        "allowed_features": "ALL", # All access
        "limits": {} # No limits
    }
}

def get_plan_rules(plan_type: str):
    """Returns the config for a specific user plan."""
    return PLAN_CONFIG.get(plan_type, PLAN_CONFIG["free"])