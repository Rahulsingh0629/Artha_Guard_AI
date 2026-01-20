from fastapi import APIRouter
from pydantic import BaseModel
from app.agents.new_sentiment.news_agent import NewsIntelligenceAgent


router = APIRouter()
news_bot = NewsIntelligenceAgent()

class NewsRequest(BaseModel):
    query: str

@router.post("/news-analysis")
def analyze_news(request: NewsRequest):
   
    response = news_bot.get_intelligence(request.query)
    return {"ai_response": response}