import os
import re
from typing import Dict, Any
from dotenv import load_dotenv

try:
    import google.generativeai as genai
except Exception:
    genai = None

load_dotenv()


class AdvisoryAI:
    def __init__(self):
        self.api_key = os.getenv("GEMINI_API_KEY")
        self.model = None

        if self.api_key and genai is not None:
            try:
                genai.configure(api_key=self.api_key)
                self.model = genai.GenerativeModel("gemini-flash-latest")
            except Exception:
                self.model = None

    def _offline_advice(self, user_query: str, user_profile: Dict[str, Any]) -> str:
        risk = user_profile.get("risk_category", "MODERATE")
        horizon = user_profile.get("horizon", "5 years")
        q = (user_query or "").strip()

        if not q:
            return "Share your goal, budget, and timeline, and I will suggest a practical plan."

        q_lower = q.lower()
        sip_match = re.search(r"(\d[\d,]*)", q)
        sip_hint = sip_match.group(1) if sip_match else "10000"

        if "sip" in q_lower or "mutual fund" in q_lower:
            return (
                f"For {risk} risk and {horizon} horizon, split SIP roughly into: "
                "60% large-cap index, 20% flexi-cap, 20% debt/gilt. "
                f"If your monthly SIP is Rs. {sip_hint}, rebalance every 6 months."
            )
        if "stock" in q_lower or "nifty" in q_lower or "sensex" in q_lower:
            return (
                "Use a core-satellite approach: 70% diversified index/core holdings and 30% satellite ideas. "
                "Keep max 10-12% in one stock and always track valuation + earnings."
            )
        if "tax" in q_lower:
            return (
                "For India, review 80C/80D, choose tax-efficient holding periods, and avoid frequent short-term exits. "
                "Maintain transaction records for accurate capital gains filing."
            )

        return (
            "I can help with investing, risk, SIP planning, portfolio allocation, and tax-aware strategy in Indian markets. "
            "Tell me your monthly investable amount, goal, and time horizon for a tailored answer."
        )

    def get_advice(self, user_query: str, user_profile: Dict[str, Any], portfolio_summary: str) -> str:
        if self.model is None:
            return self._offline_advice(user_query=user_query, user_profile=user_profile)

        prompt = f"""
        User Context (For reference only):
        - Knowledge Level/Risk: {user_profile.get('risk_category', 'General User')}
        - Current Holdings: {portfolio_summary}

        User's Question:
        \"{user_query}\"

        Task:
        Please provide the best, most helpful answer to the user's question above.
        - Adapt your explanation to match the user's likely understanding level.
        - If the question is about finance, use the Indian context (Nifty/Sensex).
        - If the question is general (e.g., \"How are you?\"), answer naturally.
        - Be clear, concise, and friendly.
        """

        try:
            response = self.model.generate_content(prompt)
            return response.text or self._offline_advice(user_query=user_query, user_profile=user_profile)
        except Exception as e:
            error_msg = str(e)
            if "429" in error_msg or "Quota exceeded" in error_msg:
                return "I'm receiving too many requests. Please wait 30 seconds and try again."
            return self._offline_advice(user_query=user_query, user_profile=user_profile)
