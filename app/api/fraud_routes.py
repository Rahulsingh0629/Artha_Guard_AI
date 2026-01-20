from fastapi import APIRouter, HTTPException, UploadFile, File, Form, Depends
from pydantic import BaseModel
from typing import Optional
import io
from PIL import Image
import json

from app.agents.fraud_engine.tip_analyzer import TipIntegrityAgent
from app.auth.jwt_manager import get_current_user
from app.database.models import User

router = APIRouter()

@router.post("/check_tip")
async def check_fraud_unified(
    message_content: Optional[str] = Form(None), 
    sender_source: str = Form(...),
    file: Optional[UploadFile] = File(None),
    current_user: User = Depends(get_current_user)
):
    
    try:
        agent = TipIntegrityAgent()
        
        image_obj = None
        if file:
            contents = await file.read()
            image_obj = Image.open(io.BytesIO(contents))
        
        result = agent.analyze_tip(
            source=sender_source,
            text_input=message_content,
            image_input=image_obj
        )
        
        return {
            "status": "success",
            "user": current_user.email,
            "input_type": "Mixed" if (image_obj and message_content) else ("Image" if image_obj else "Text"),
            "analysis": result
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Analysis Failed: {str(e)}")