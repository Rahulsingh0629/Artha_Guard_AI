import nltk
from nltk.sentiment.vader import SentimentIntensityAnalyzer
from dataclasses import dataclass

# Download VADER lexicon (run once)
try:
    nltk.data.find('sentiment/vader_lexicon.zip')
except LookupError:
    nltk.download('vader_lexicon')

@dataclass
class SentimentScore:
    compound: float  # -1 (Most Negative) to +1 (Most Positive)
    label: str       # BULLISH, BEARISH, NEUTRAL
    confidence: float

class FinancialSentimentEngine:
    """
    Analyzes text to determine financial sentiment.
    """
    def __init__(self):
        self.analyzer = SentimentIntensityAnalyzer()

    def analyze(self, text: str) -> SentimentScore:
        scores = self.analyzer.polarity_scores(text)
        compound = scores['compound']

        # Financial Sentiment Thresholds
        if compound >= 0.05:
            label = "BULLISH"
        elif compound <= -0.05:
            label = "BEARISH"
        else:
            label = "NEUTRAL"

        # Confidence is the absolute strength of the sentiment
        confidence = round(abs(compound) * 100, 1)

        return SentimentScore(
            compound=compound,
            label=label,
            confidence=confidence
        )