import logging
import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import List, Dict, Any
from datetime import datetime
from sqlalchemy.orm import Session
from twilio.rest import Client

from app.agents.intraday_scanner.scanner import MarketScanner
from app.agents.new_sentiment.news_agent import NewsIntelligenceAgent
from app.database.models import User

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("AlertAgent")

class AlertAgent:
    """
    Smart Market Monitor (24/7).
    Features:
    - Anti-Spam (No duplicate alerts per day)
    - Rate Limiting (Max 5 emails/day per user)
    - High-Importance Filtering
    """

    def __init__(self):
        self.scanner = MarketScanner()
        self.news_bot = NewsIntelligenceAgent()
        
        # --- MEMORY (Resets when you restart the worker) ---
        # Stores what we sent today: {(user_id, symbol, type): "2023-12-25"}
        self.sent_history = {} 
        # Stores count per user: {user_id: 3}
        self.daily_counts = {}
        self.last_reset_date = datetime.now().date()

        self.market_watchlist = [
            "RELIANCE", "TATASTEEL", "HDFCBANK", "INFY", "SBIN", "ICICIBANK", 
            "ADANIENT", "WIPRO", "ITC", "LT", "AXISBANK", "MARUTI", "TITAN",
            "ULTRACEMCO", "BAJFINANCE", "ASIANPAINT", "TCS", "KOTAKBANK"
        ]

    def _reset_daily_limits_if_new_day(self):
        """Checks if the date has changed. If yes, wipe the memory."""
        today = datetime.now().date()
        if today > self.last_reset_date:
            logger.info("📅 New Day Detected! Resetting daily alert limits.")
            self.sent_history.clear()
            self.daily_counts.clear()
            self.last_reset_date = today

    def run_monitoring_cycle(self, db: Session) -> Dict[str, Any]:
        self._reset_daily_limits_if_new_day()
        
        market_data = self.scanner.scan_watchlist(self.market_watchlist)
        alerts_generated = []

        for data in market_data:
            if "error" in data:
                continue

            symbol = data['symbol']
            price = data['current_price']
            rsi = data.get('rsi', 50)
            
            # --- TIGHTER LOGIC (Only Important Stuff) ---
            # Changed RSI from 30 to 25 (Only SUPER cheap stocks)
            if rsi < 25: 
                news_analysis = self.news_bot.get_intelligence(symbol)
                headline = self._extract_headline(news_analysis)
                message = self._generate_msg("OPPORTUNITY", symbol, price, "Deeply Undervalued", headline, "Strong Buy Zone.")
                self._broadcast_smart_alert(db, message, symbol, "OPPORTUNITY", f"🚀 Buy Opportunity: {symbol}")
                alerts_generated.append(message)

            # Changed RSI from 75 to 80 (Only SUPER expensive stocks)
            elif rsi > 80:
                news_analysis = self.news_bot.get_intelligence(symbol)
                headline = self._extract_headline(news_analysis)
                message = self._generate_msg("RISK", symbol, price, "Dangerous Highs", headline, "High Crash Risk.")
                self._broadcast_smart_alert(db, message, symbol, "RISK", f"⚠️ Risk Alert: {symbol}")
                alerts_generated.append(message)

            elif data.get('volume_change_pct', 0) > 60: # Increased to 60%
                news_analysis = self.news_bot.get_intelligence(symbol)
                headline = self._extract_headline(news_analysis)
                message = self._generate_msg("MOMENTUM", symbol, price, "Extreme Volume", headline, "Explosive movement detected.")
                self._broadcast_smart_alert(db, message, symbol, "MOMENTUM", f"🔥 Momentum: {symbol}")
                alerts_generated.append(message)

        return {
            "stocks_scanned": len(market_data),
            "alerts_sent": len(alerts_generated),
            "details": alerts_generated
        }

    def _broadcast_smart_alert(self, db: Session, message_body: str, symbol: str, alert_type: str, subject: str):
        """
        Sends alerts ONLY if:
        1. User hasn't received THIS specific alert today.
        2. User hasn't exceeded 5 emails today.
        """
        users = db.query(User).all()
        
        for user in users:
            user_id = user.id
            
            # --- CHECK 1: DAILY LIMIT (Max 5) ---
            current_count = self.daily_counts.get(user_id, 0)
            if current_count >= 5:
                logger.info(f"🚫 Skipped {user.email}: Daily limit reached ({current_count}/5)")
                continue

            # --- CHECK 2: DUPLICATE CHECK ---
            # Key = (User ID, Stock Name, Alert Type)
            # Example: (1, "TATASTEEL", "OPPORTUNITY")
            alert_key = (user_id, symbol, alert_type)
            
            if alert_key in self.sent_history:
                # We already sent this alert to this user today
                continue 

            # --- SENDING ---
            sent_success = False
            
            for user in users:
            # 1. Send SMS (if phone exists)
             if user.phone_number is not None:
                self._send_sms_notification(str(user.phone_number), message_body)

            # 2. Send Email (if email exists)
             if user.email is not None:
                self._send_email_notification(str(user.email), subject, message_body)

            # --- UPDATE MEMORY ---
             if sent_success:
                self.sent_history[alert_key] = True
                self.daily_counts[user_id] = current_count + 1
                logger.info(f"✅ Alert sent to {user.email} (Count: {current_count + 1}/5)")

    def _generate_msg(self, type, symbol, price, context, news, prediction):
        return (
            f"📢 ArthaGuard {type}\n"
            f"Stock: {symbol}\n"
            f"Price: ₹{price}\n"
            f"Status: {context}\n"
            f"News: {news}\n"
            f"AI Verdict: {prediction}"
        )

    def _extract_headline(self, news_summary: str) -> str:
        try:
            lines = news_summary.split('\n')
            for line in lines:
                if "🟢" in line or "🔴" in line or "[" in line:
                    return line.strip()[:50] + "..." # Truncate to keep SMS short
            return "Market sentiment mixed."
        except:
            return "N/A"

    def _send_sms_notification(self, phone_number: str, message: str):
        try:
            account_sid = os.getenv("TWILIO_SID")
            auth_token = os.getenv("TWILIO_AUTH_TOKEN")
            from_number = os.getenv("TWILIO_PHONE_NUMBER")
            if account_sid:
                client = Client(account_sid, auth_token)
                client.messages.create(body=message, from_=from_number, to=phone_number)
        except Exception:
            pass # Silent fail to keep logs clean

    def _send_email_notification(self, to_email: str, subject: str, body: str):
        try:
            smtp_server = os.getenv("SMTP_SERVER", "smtp.gmail.com")
            smtp_port = int(os.getenv("SMTP_PORT", "587"))
            sender_email = os.getenv("EMAIL_SENDER")
            sender_password = os.getenv("EMAIL_PASSWORD")

            if not sender_email or not sender_password:
                return

            msg = MIMEMultipart()
            msg['From'] = sender_email
            msg['To'] = to_email
            msg['Subject'] = subject
            msg.attach(MIMEText(body, 'plain'))

            server = smtplib.SMTP(smtp_server, smtp_port)
            server.starttls()
            server.login(sender_email, sender_password)
            server.send_message(msg)
            server.quit()
        except Exception as e:
            logger.error(f"Email Error: {e}")