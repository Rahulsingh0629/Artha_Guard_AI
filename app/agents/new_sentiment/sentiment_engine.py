import nltk
from nltk.sentiment.vader import SentimentIntensityAnalyzer
from dataclasses import dataclass

try:
    nltk.data.find('sentiment/vader_lexicon.zip')
except LookupError:
    nltk.download('vader_lexicon')

@dataclass
class SentimentScore:
    compound: float  
    label: str       
    confidence: float

class FinancialSentimentEngine:
    
    def __init__(self):
        self.analyzer = SentimentIntensityAnalyzer()

    def analyze(self, text: str) -> SentimentScore:
        scores = self.analyzer.polarity_scores(text)
        compound = scores['compound']

        
        if compound >= 0.05:
            label = "BULLISH"
        elif compound <= -0.05:
            label = "BEARISH"
        else:
            label = "NEUTRAL"

        
        confidence = round(abs(compound) * 100, 1)

        return SentimentScore(
            compound=compound,
            label=label,
            confidence=confidence
        )