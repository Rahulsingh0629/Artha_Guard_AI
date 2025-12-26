import requests
import os
import logging
from typing import List, Dict, Optional
from datetime import datetime, timedelta
from dotenv import load_dotenv

# Import your engine (ensure this file exists in the same directory)
from .sentiment_engine import FinancialSentimentEngine

# Load environment variables from .env file
load_dotenv()

# Configure logging to track issues in production
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("NewsAggregator")

class NewsAggregator:
    def __init__(self):
        # 1. Securely fetch key from environment
        self.api_key = os.getenv("NEWS_API_KEY")
        self.sentiment_engine = FinancialSentimentEngine()
        self.base_url = "https://newsapi.org/v2/everything"
        

    def fetch_market_news(self, query: str = "Indian Stock Market") -> List[Dict]:
        """
        Fetches news, analyzes sentiment in real-time, and returns structured data.
        Automatically falls back to mock data on failure.
        """
        # 2. Check for missing key before making a useless network call
        if not self.api_key:
            return self._get_mock_news(query)

        try:
            # 3. Optimize parameters for relevance
            # Fetch last 3 days only to keep data fresh and reduce noise
            from_date = (datetime.now() - timedelta(days=3)).strftime('%Y-%m-%d')
            
            params = {
                "q": query,
                "from": from_date,
                "sortBy": "popularity",
                "language": "en",
                "apiKey": self.api_key
            }

            # 4. CRITICAL: Add timeout to prevent hanging forever
            response = requests.get(self.base_url, params=params, timeout=10)
            data = response.json()
            
            # 5. Handle API-specific errors (e.g., Rate Limit Exceeded)
            if response.status_code != 200 or data.get("status") != "ok":
                logger.error(f"NewsAPI Error: {data.get('message', 'Unknown Error')}")
                return self._get_mock_news(query) # Fallback

            analyzed_news = []
            
            # Process only top 5 articles to save compute time
            for article in data.get("articles", [])[:5]:
                title = article.get("title")
                description = article.get("description") or ""
                
                # Skip removed/empty articles common in NewsAPI
                if not title or title == "[Removed]":
                    continue

                # Analyze Sentiment on combined text
                full_text = f"{title}. {description}"
                sentiment = self.sentiment_engine.analyze(full_text)

                analyzed_news.append({
                    "source": article["source"]["name"],
                    "title": title,
                    "url": article["url"],
                    "published_at": article["publishedAt"],
                    "sentiment_label": sentiment.label,
                    "sentiment_score": sentiment.confidence
                })
            
            # If API returned 0 results, show mock data so user sees something
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

    def _get_mock_news(self, query: str) -> List[Dict]:
        """Fallback mock data used when API fails or is missing."""
        mock_data = [
            {"title": f"{query} sees massive institutional inflow", "source": "Bloomberg"},
            {"title": f"Regulatory updates expected for {query} next week", "source": "Reuters"},
            {"title": f"Analysts predict strong Q4 for {query} giants", "source": "Mint"},
        ]
        
        results = []
        for news in mock_data:
            sentiment = self.sentiment_engine.analyze(news['title'])
            results.append({
                "source": news['source'],
                "title": news['title'],
                "url": "https://example.com",
                "published_at": datetime.now().isoformat(),
                "sentiment_label": sentiment.label,
                "sentiment_score": sentiment.confidence
            })
        return results