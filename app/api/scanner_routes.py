from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from app.agents.intraday_scanner.probability_ranker import FinancialAdvisorAgent
from app.agents.intraday_scanner.scanner import MarketScanner 

router = APIRouter()

class ChatRequest(BaseModel):
    user_id: str
    message: str

class ChatResponse(BaseModel):
    response: str
    data_source: str = "ArthaGuard AI Engine"

advisor_agent = FinancialAdvisorAgent()

@router.post("/chat", response_model=ChatResponse)
async def chat_endpoint(request: ChatRequest):
    try:
        ai_reply = advisor_agent.get_response(request.message)
        
        return ChatResponse(response=ai_reply)
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/scan/market")
async def scan_market():
    tool = MarketScanner()
    
    watch_list = ["RELIANCE", "TATASTEEL", "HDFCBANK", "INFY", "SBIN"]
    return tool.scan_watchlist(watch_list)