import requests
import os
import logging
from typing import List, Dict, Optional
from datetime import datetime, timedelta
from dotenv import load_dotenv
from urllib.parse import quote_plus

from .sentiment_engine import FinancialSentimentEngine

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("NewsAggregator")

class NewsAggregator:
    def __init__(self):
        
        self.api_key = os.getenv("NEWS_API_KEY")
        self.sentiment_engine = FinancialSentimentEngine()
        self.base_url = "https://newsapi.org/v2/everything"
        

    def _build_article(self, article: Dict) -> Optional[Dict]:
        title = article.get("title")
        description = article.get("description") or ""

        if not title or title == "[Removed]":
            return None

        full_text = f"{title}. {description}"
        sentiment = self.sentiment_engine.analyze(full_text)

        return {
            "source": article.get("source", {}).get("name", "Unknown"),
            "title": title,
            "description": description,
            "url": article.get("url"),
            "image_url": article.get("urlToImage"),
            "published_at": article.get("publishedAt"),
            "sentiment_label": sentiment.label,
            "sentiment_score": sentiment.confidence,
        }

    def fetch_market_news(self, query: str = "Indian Stock Market") -> List[Dict]:
       
        if not self.api_key:
            return self._get_mock_news(query)

        try:
           
            from_date = (datetime.now() - timedelta(days=3)).strftime('%Y-%m-%d')
            
            params = {
                "q": query,
                "from": from_date,
                "sortBy": "popularity",
                "language": "en",
                "apiKey": self.api_key
            }

            response = requests.get(self.base_url, params=params, timeout=10)
            data = response.json()
            
            if response.status_code != 200 or data.get("status") != "ok":
                logger.error(f"NewsAPI Error: {data.get('message', 'Unknown Error')}")
                return self._get_mock_news(query) # Fallback

            analyzed_news = []
            for article in data.get("articles", [])[:5]:
                prepared = self._build_article(article)
                if prepared:
                    analyzed_news.append(prepared)
            
            if not analyzed_news:
                logger.info(f"No live news found for {query}. Switching to mock.")
                return self._get_mock_news(query)

            return analyzed_news

        except requests.exceptions.Timeout:
            logger.error("NewsAPI request timed out.")
            return self._get_mock_news(query)
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Network Error: {e}")
            return self._get_mock_news(query)

        except Exception as e:
            logger.error(f"Unexpected Error: {e}")
            return self._get_mock_news(query)

    def fetch_market_feed(
        self,
        search: str = "",
        page: int = 1,
        page_size: int = 20,
    ) -> Dict:
        effective_query = (
            search.strip()
            if search and search.strip()
            else "Indian stock market OR NSE OR BSE OR Nifty OR Sensex"
        )

        if not self.api_key:
            items = self._get_mock_news(effective_query, count=page_size, days=5)
            return {
                "query": effective_query,
                "page": page,
                "page_size": page_size,
                "total_results": len(items),
                "items": items,
                "is_mock": True,
            }

        try:
            from_date = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")
            params = {
                "q": effective_query,
                "from": from_date,
                "sortBy": "publishedAt",
                "language": "en",
                "page": page,
                "pageSize": page_size,
                "apiKey": self.api_key,
            }
            response = requests.get(self.base_url, params=params, timeout=12)
            data = response.json()
            if response.status_code != 200 or data.get("status") != "ok":
                logger.error(f"NewsAPI feed error: {data.get('message', 'Unknown Error')}")
                items = self._get_mock_news(effective_query, count=page_size, days=5)
                return {
                    "query": effective_query,
                    "page": page,
                    "page_size": page_size,
                    "total_results": len(items),
                    "items": items,
                    "is_mock": True,
                }

            items = []
            for article in data.get("articles", []):
                prepared = self._build_article(article)
                if prepared:
                    if not prepared.get("image_url"):
                        prepared["image_url"] = (
                            f"https://source.unsplash.com/800x450/?stock-market,{quote_plus(effective_query)}"
                        )
                    items.append(prepared)

            return {
                "query": effective_query,
                "page": page,
                "page_size": page_size,
                "total_results": int(data.get("totalResults", len(items))),
                "items": items,
                "is_mock": False,
            }
        except Exception as e:
            logger.error(f"News feed fallback due to error: {e}")
            items = self._get_mock_news(effective_query, count=page_size, days=5)
            return {
                "query": effective_query,
                "page": page,
                "page_size": page_size,
                "total_results": len(items),
                "items": items,
                "is_mock": True,
            }

    def _get_mock_news(self, query: str, count: int = 3, days: int = 3) -> List[Dict]:
       
        mock_data = [
            {"title": f"{query} sees massive institutional inflow", "source": "Bloomberg"},
            {"title": f"Regulatory updates expected for {query} next week", "source": "Reuters"},
            {"title": f"Analysts predict strong Q4 for {query} giants", "source": "Mint"},
            {"title": f"NSE volatility rises as traders track {query}", "source": "Economic Times"},
            {"title": f"Sector rotation visible in {query} counters", "source": "Business Standard"},
        ]

        results = []
        for i, news in enumerate(mock_data[:count]):
            sentiment = self.sentiment_engine.analyze(news['title'])
            published_at = (datetime.now() - timedelta(hours=min(i * 6, days * 24))).isoformat()
            results.append({
                "source": news['source'],
                "title": news['title'],
                "description": f"Auto-generated fallback headline for {query}.",
                "url": "https://example.com",
                "image_url": "https://source.unsplash.com/800x450/?stock-market",
                "published_at": published_at,
                "sentiment_label": sentiment.label,
                "sentiment_score": sentiment.confidence
            })
        return results
