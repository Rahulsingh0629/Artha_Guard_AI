from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

# --- CORRECT IMPORTS ---
# The Agent lives in probability_ranker.py
from app.agents.intraday_scanner.probability_ranker import FinancialAdvisorAgent
# The Scanner tool lives in scanner.py
from app.agents.intraday_scanner.scanner import MarketScanner 

router = APIRouter()

class ChatRequest(BaseModel):
    user_id: str
    message: str

class ChatResponse(BaseModel):
    response: str
    data_source: str = "ArthaGuard AI Engine"

# Initialize Agent once (Singleton pattern)
advisor_agent = FinancialAdvisorAgent()

@router.post("/chat", response_model=ChatResponse)
async def chat_endpoint(request: ChatRequest):
    try:
        # The agent handles the complexity (Intent -> Tool -> Response)
        ai_reply = advisor_agent.get_response(request.message)
        
        return ChatResponse(response=ai_reply)
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# --- OPTIONAL: Direct Scanner Endpoint ---
@router.get("/scan/market")
async def scan_market():
    """Returns raw data for the Dashboard UI"""
    # FIX: Use the correct class name 'MarketScanner'
    tool = MarketScanner()
    
    # In prod, fetch these from a database
    watch_list = ["RELIANCE", "TATASTEEL", "HDFCBANK", "INFY", "SBIN"]
    return tool.scan_watchlist(watch_list)