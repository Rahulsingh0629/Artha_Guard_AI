from .news_aggregator import NewsAggregator

class NewsIntelligenceAgent:
   
    def __init__(self):
        self.aggregator = NewsAggregator()

    def get_intelligence(self, user_query: str) -> str:
        
        topic = self._extract_topic(user_query)
        
        news_items = self.aggregator.fetch_market_news(topic)
        
        if not news_items:
            return f"I couldn't find any recent news specifically about '{topic}'."

        bullish_count = sum(1 for n in news_items if n['sentiment_label'] == 'BULLISH')
        bearish_count = sum(1 for n in news_items if n['sentiment_label'] == 'BEARISH')
        
        overall_mood = "NEUTRAL"
        if bullish_count > bearish_count: overall_mood = "POSITIVE"
        if bearish_count > bullish_count: overall_mood = "NEGATIVE"

        response = f"**News Analysis for: {topic}**\n"
        response += f"📉 Overall Market Mood: **{overall_mood}**\n\n"
        response += "**Top Headlines:**\n"
        
        for item in news_items:
            emoji = "🟢" if item['sentiment_label'] == "BULLISH" else "🔴" if item['sentiment_label'] == "BEARISH" else "⚪"
            response += f"{emoji} [{item['source']}] {item['title']}\n"
            response += f"   *(Sentiment: {item['sentiment_label']} {item['sentiment_score']}% confidence)*\n\n"
            
        return response

    def _extract_topic(self, query: str) -> str:
        
        ignore_words = ["news", "about", "what", "is", "the", "on", "latest", "give", "me", "tell"]
        words = query.lower().split()
        keywords = [w for w in words if w not in ignore_words]
        
        if keywords:
            return " ".join(keywords).title()
        return "Indian Stock Market"