import google.generativeai as genai
import os
from typing import Dict, Any

class AdvisoryAI:
    def __init__(self):
        # 🔑 GET YOUR KEY HERE: https://aistudio.google.com/app/apikey
        self.api_key = os.getenv("GEMINI_API_KEY")
        
        if not self.api_key:
            raise ValueError("GEMINI_API_KEY not found. Please set it in your .env file.")
            
        genai.configure(api_key=self.api_key)
        print("🚀 DEBUG: Loading Model GEMINI-1.5-FLASH")
        self.model = genai.GenerativeModel('gemini-1.5-flash')

    def get_advice(self, user_query: str, user_profile: Dict[str, Any], portfolio_summary: str) -> str:
        """
        Generates a highly contextual financial answer using Gemini AI.
        """
        
        # 1. Construct the "System Persona"
        # We tell the AI exactly who it is and how to behave.
        system_prompt = f"""
        ROLE: You are 'ArthaGuard', an elite AI Wealth Manager for the Indian Market (NSE/BSE).
        
        USER CONTEXT:
        - Risk Profile: {user_profile.get('risk_category', 'Unknown')}
        - Investment Horizon: {user_profile.get('horizon', 'Long Term')}
        - Current Portfolio: {portfolio_summary}
        
        USER QUESTION: "{user_query}"
        
        INSTRUCTIONS:
        1. Answer specifically for the Indian context (mention Nifty, Sensex, SEBI rules if relevant).
        2. Be professional, concise, and empathetic.
        3. If the user asks for 'Tips' (gambling), strictly warn them about risks.
        4. Use bullet points for clarity.
        5. Disclaimer: Always end with 'I am an AI, not a SEBI registered advisor.'
        """
        
        try:
            # 2. Call Google Gemini
            response = self.model.generate_content(system_prompt)
            return response.text
        except Exception as e:
            # Fallback if AI service is down
            return f"My AI brain is currently reconnecting. Please try again. (Error: {str(e)})"