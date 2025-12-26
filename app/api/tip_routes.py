# from fastapi import APIRouter, Depends, HTTPException
# from sqlalchemy.orm import Session
# from pydantic import BaseModel
# from typing import cast

# # Correct Imports
# from app.database.session import get_db
# from app.database.models import User
# from app.auth.jwt_manager import get_current_user
# from app.subscription.feature_guard import FeatureGuard, AccessDeniedError
# from app.subscription.plan_checker import FeatureName

# # Import the Agent
# from app.agents.fraud_engine.detector import FakeTipDetector

# router = APIRouter()

# # --- INPUT SCHEMA ---
# class TipCheckRequest(BaseModel):
#     tip_text: str

# # --- THE API ROUTE ---
# @router.post("/check")
# def check_fake_tip(
#     request: TipCheckRequest, 
#     db: Session = Depends(get_db), 
#     current_user: User = Depends(get_current_user)
# ):
#     """
#     Analyzes a stock tip. 
#     Secured by FeatureGuard (Free users limited).
#     """
    
#     # 1. THE GUARD
#     try:
#         FeatureGuard.check_access(db, current_user, FeatureName.FAKE_TIP_CHECK)
#     except AccessDeniedError as e:
#         raise HTTPException(status_code=403, detail=str(e))

#     # 2. THE LOGIC
#     detector = FakeTipDetector()
#     result = detector.analyze(request.tip_text)

#     # 3. THE LOG (Update usage count)
#     FeatureGuard.log_usage(db, cast(int, current_user.id), FeatureName.FAKE_TIP_CHECK)

#     return {
#         "status": "success",
#         "plan": current_user.plan_type.value,
#         "analysis": result
#     }