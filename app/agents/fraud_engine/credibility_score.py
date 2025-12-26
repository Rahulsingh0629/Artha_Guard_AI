# import re

# class CredibilityScorer:
    
#     # 1. SCAM KEYWORDS (High Risk)
#     SCAM_KEYWORDS = [
#         "guaranteed", "100% profit", "sure shot", "jackpot", 
#         "multibagger", "rocket", "blast", "confirmed news", 
#         "insider info", "operator move", "circuit to circuit"
#     ]

#     # 2. URGENCY KEYWORDS (Medium Risk)
#     URGENCY_KEYWORDS = [
#         "hurry", "buy now", "urgent", "limited time", 
#         "don't miss", "last chance", "gap up opening"
#     ]

#     @staticmethod
#     def calculate_risk_score(text: str) -> dict:
#         """
#         Analyzes text and returns a risk score (0-100).
#         0 = Safe, 100 = Scam.
#         """
#         text_lower = text.lower()
#         score = 0
#         reasons = []

#         # Check for Scam Keywords (+15 points each)
#         for word in CredibilityScorer.SCAM_KEYWORDS:
#             if word in text_lower:
#                 score += 15
#                 reasons.append(f"Contains hype word: '{word}'")

#         # Check for Urgency (+10 points each)
#         for word in CredibilityScorer.URGENCY_KEYWORDS:
#             if word in text_lower:
#                 score += 10
#                 reasons.append(f"Creates false urgency: '{word}'")

#         # Check for Caps Lock Abuse (YELLING) (+10 points)
#         # If more than 40% of the text is uppercase
#         if len(text) > 10:
#             upper_case_count = sum(1 for c in text if c.isupper())
#             if (upper_case_count / len(text)) > 0.4:
#                 score += 10
#                 reasons.append("Excessive use of CAPS LOCK")

#         # Check for Emoji Spam (+5 points)
#         emoji_count = len(re.findall(r'[^\w\s,.]', text))
#         if emoji_count > 3:
#             score += 5
#             reasons.append("Excessive emojis used to hype")

#         # Cap the score at 100
#         score = min(score, 100)

#         # Determine Verdict
#         if score > 75:
#             verdict = "SCAM"
#         elif score > 40:
#             verdict = "SUSPICIOUS"
#         else:
#             verdict = "SAFE"

#         return {
#             "score": score,
#             "verdict": verdict,
#             "reasons": reasons
#         }