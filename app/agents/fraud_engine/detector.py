# import re
# from app.agents.fraud_engine.credibility_score import CredibilityScorer

# class FakeTipDetector:
    
#     def analyze(self, tip_text: str):
#         """
#         Main entry point for the agent.
#         Input: "Buy TATASTEEL now! 100% guarantee!"
#         Output: Full analysis report.
#         """
        
#         # 1. Run the scoring logic
#         risk_analysis = CredibilityScorer.calculate_risk_score(tip_text)
        
#         # 2. Extract Stock Symbol (Basic Regex for NSE/BSE)
#         # Looks for words in ALL CAPS that are 3-10 letters long
#         potential_stocks = self._extract_tickers(tip_text)

#         # 3. Construct the Final Report
#         return {
#             "original_text": tip_text,
#             "detected_stocks": potential_stocks,
#             "risk_score": risk_analysis["score"],     # e.g., 85
#             "risk_level": risk_analysis["verdict"],   # e.g., "SCAM"
#             "flags": risk_analysis["reasons"],        # List of bad things found
#             "recommendation": self._get_recommendation(risk_analysis["verdict"])
#         }

#     def _extract_tickers(self, text: str) -> list:
#         """
#         Simple regex to find potential stock symbols (e.g., INFY, HDFC).
#         """
#         # Find all uppercase words of length 3-9
#         matches = re.findall(r'\b[A-Z]{3,9}\b', text)
        
#         # Filter out common English words (False Positives)
#         common_words = ["THE", "AND", "FOR", "BUY", "SELL", "NOW", "THIS", "NSE", "BSE"]
#         stocks = [word for word in matches if word not in common_words]
        
#         return list(set(stocks)) # Remove duplicates

#     def _get_recommendation(self, verdict: str) -> str:
#         if verdict == "SCAM":
#             return "DANGER: Do not trade. This message shows high signs of manipulation."
#         elif verdict == "SUSPICIOUS":
#             return "CAUTION: Verify this information with official news sources before trading."
#         else:
#             return "LOW RISK: The language seems neutral, but always do your own research."