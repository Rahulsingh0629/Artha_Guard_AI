from fastapi import APIRouter
from pydantic import BaseModel
from app.agents.new_sentiment.news_agent import NewsIntelligenceAgent
from app.agents.new_sentiment.news_aggregator import NewsAggregator
from datetime import datetime, timezone, timedelta


router = APIRouter()
news_bot = NewsIntelligenceAgent()
news_aggregator = NewsAggregator()
IST = timezone(timedelta(hours=5, minutes=30))

class NewsRequest(BaseModel):
    query: str

@router.post("/news-analysis")
def analyze_news(request: NewsRequest):
   
    response = news_bot.get_intelligence(request.query)
    return {"ai_response": response}


@router.get("/feed")
def get_news_feed(
    q: str = "",
    page: int = 1,
    page_size: int = 20,
):
    safe_page = max(page, 1)
    safe_page_size = min(max(page_size, 10), 50)

    feed = news_aggregator.fetch_market_feed(
        search=q,
        page=safe_page,
        page_size=safe_page_size,
    )
    items = feed.get("items", [])

    now_ist = datetime.now(IST)
    latest_today = []
    for item in items:
        published_at = item.get("published_at")
        if not published_at:
            continue
        try:
            dt = datetime.fromisoformat(str(published_at).replace("Z", "+00:00"))
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            dt_ist = dt.astimezone(IST)
            if dt_ist.date() == now_ist.date():
                latest_today.append(item)
        except Exception:
            continue

    return {
        **feed,
        "latest_today": latest_today,
        "server_time": datetime.now(timezone.utc).isoformat(),
        "server_time_ist": now_ist.isoformat(),
        "timezone": "Asia/Kolkata",
    }
