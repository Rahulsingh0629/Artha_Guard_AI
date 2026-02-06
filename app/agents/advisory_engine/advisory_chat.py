import google.generativeai as genai
import os
from typing import Dict, Any
from dotenv import load_dotenv

load_dotenv()

class AdvisoryAI:
    def __init__(self):
        # 🔑 GET YOUR KEY HERE: https://aistudio.google.com/app/apikey
        self.api_key = os.getenv("GEMINI_API_KEY")
        
        if not self.api_key:
            raise ValueError("GEMINI_API_KEY not found. Please set it in your .env file.")
            
        genai.configure(api_key=self.api_key)
        
        self.model = genai.GenerativeModel('gemini-flash-latest')

    def get_advice(self, user_query: str, user_profile: Dict[str, Any], portfolio_summary: str) -> str:
        prompt = f"""
        User Context (For reference only):
        - Knowledge Level/Risk: {user_profile.get('risk_category', 'General User')}
        - Current Holdings: {portfolio_summary}

        User's Question:
        "{user_query}"

        Task:
        Please provide the best, most helpful answer to the user's question above.
        - Adapt your explanation to match the user's likely understanding level.
        - If the question is about finance, use the Indian context (Nifty/Sensex).
        - If the question is general (e.g., "How are you?"), answer naturally.
        - Be clear, concise, and friendly.
        """
        
        try:
            
            response = self.model.generate_content(prompt)
            return response.text
            
        except Exception as e:
            error_msg = str(e)
            if "429" in error_msg or "Quota exceeded" in error_msg:
                return "I'm receiving too many requests. Please wait 30 seconds and try again."
            
            return f"I'm having trouble connecting right now. Please try again. (Error: {error_msg})"