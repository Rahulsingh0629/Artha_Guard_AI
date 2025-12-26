import os
import json
import google.generativeai as genai
from PIL import Image
from typing import Dict, Any, Optional

# Import your existing News Agent
from app.agents.new_sentiment.news_agent import NewsIntelligenceAgent

class TipIntegrityAgent:
    def __init__(self):
        self.api_key = os.getenv("GEMINI_API_KEY")
        if not self.api_key:
            raise ValueError("GEMINI_API_KEY is missing!")
        
        genai.configure(api_key=self.api_key)
        # Gemini 1.5 Flash is best for Mixed Inputs (Text + Image)
        self.model = genai.GenerativeModel('gemini-1.5-flash')
        self.news_bot = NewsIntelligenceAgent()

    def analyze_tip(self, source: str, text_input: Optional[str] = None, image_input: Optional[Image.Image] = None) -> Dict[str, Any]:
        """
        Unified function to analyze Text, Image, or Both.
        """
        
        # 1. Validation: Ensure we have at least something to check
        if not text_input and not image_input:
            return {"verdict": "ERROR", "reason": "No input provided. Please provide text or an image."}

        # 2. Construct the Gemini Input List
        gemini_inputs = []
        
        # The System Prompt
        system_prompt = (
            "You are the 'ArthaGuard Fraud Detection Engine'. "
            "Analyze the provided inputs (Text and/or Image) for stock market fraud. "
            "First, EXTRACT the 'Stock Symbol' and the 'Main Claim' (e.g., Target Price, Guaranteed Profit). "
            "Return JSON: {'stock_symbol': 'SYMBOL', 'claim': 'extracted claim'}"
        )
        gemini_inputs.append(system_prompt)

        # Add User Data
        if text_input:
            gemini_inputs.append(f"USER TEXT NOTE: {text_input}")
        
        if image_input:
            gemini_inputs.append(image_input) # Gemini handles the Image object directly

        # --- PHASE 1: EXTRACTION ---
        try:
            raw_result = self.model.generate_content(gemini_inputs).text
            # Clean JSON
            clean_json = raw_result.strip().replace("```json", "").replace("```", "")
            extracted_data = json.loads(clean_json)
            
            stock_symbol = extracted_data.get("stock_symbol", "UNKNOWN")
            claim = extracted_data.get("claim", "Unknown Claim")
        except:
            stock_symbol = "UNKNOWN"
            claim = "Could not extract clear claim from input."

        # --- PHASE 2: REALITY CHECK (News) ---
        news_verification = "No specific news found."
        if stock_symbol != "UNKNOWN":
            print(f"🔍 Checking News for: {stock_symbol}")
            real_news = self.news_bot.get_intelligence(stock_symbol)
            news_verification = f"Real News says: {real_news[:400]}..."

        # --- PHASE 3: FINAL VERDICT ---
        final_prompt = f"""
        ROLE: Fraud Detector.
        TASK: Compare Claim vs Reality.
        
        INPUT SOURCE: {source}
        DETECTED CLAIM: "{claim}"
        REALITY CHECK: "{news_verification}"
        
        RULES:
        1. 'Guaranteed' / 'Jackpot' = SCAM.
        2. High Target + Negative News = SCAM.
        3. Matches News = SAFE.
        
        OUTPUT JSON:
        {{
            "risk_score": (0-100),
            "verdict": "SAFE" or "SCAM" or "SUSPICIOUS",
            "extracted_text": "{claim}",
            "reason": "Brief explanation."
        }}
        """
        
        final_response = self.model.generate_content(final_prompt)
        try:
            return json.loads(final_response.text.strip().replace("```json", "").replace("```", ""))
        except:
            return {"verdict": "ERROR", "reason": "AI Parsing Failed"}