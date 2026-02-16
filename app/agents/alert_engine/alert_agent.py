import asyncio
import logging
import os
import random
import smtplib
from datetime import date, datetime, time, timedelta, timezone
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Any, Dict, List, Optional

try:
    import yfinance as yf
except Exception:
    yf = None

from app.agents.intraday_scanner.indicators import TechnicalIndicators
from app.agents.intraday_scanner.scanner import MarketScanner
from app.agents.new_sentiment.news_agent import NewsIntelligenceAgent
from app.database.models import AlertEvent, User, UserActivityLog, UserAlertPreference

logger = logging.getLogger("AlertAgent")

IST = timezone(timedelta(hours=5, minutes=30))


class AlertAgent:
    """
    Continuous profit-pick alert engine.
    - Wakes every 5-10 minutes.
    - Runs only in market hours.
    - Scans watchlist and scores future profit potential.
    - Applies once-daily backtest-based calibration.
    - Sends only ONE best stock per user each cycle.
    - Sends max 5-7 stocks/day/user.
    """

    EMAIL_LOG_ACTION = "profit_pick_email"

    def __init__(self):
        self.scanner = MarketScanner()
        self.news_bot = NewsIntelligenceAgent()

        self.scan_min_minutes = int(os.getenv("ALERT_SCAN_MIN_MINUTES", "5"))
        self.scan_max_minutes = int(os.getenv("ALERT_SCAN_MAX_MINUTES", "10"))
        self.default_daily_max_picks = int(os.getenv("ALERT_DAILY_MAX_PICKS", "7"))
        self.default_min_profit_score = int(os.getenv("ALERT_MIN_PROFIT_SCORE", "40"))

        if self.scan_min_minutes < 1:
            self.scan_min_minutes = 1
        if self.scan_max_minutes < self.scan_min_minutes:
            self.scan_max_minutes = self.scan_min_minutes
        self.default_daily_max_picks = min(max(self.default_daily_max_picks, 5), 7)
        self.default_min_profit_score = min(max(self.default_min_profit_score, 20), 90)

        self.market_watchlist = [
            "RELIANCE",
            "TATASTEEL",
            "HDFCBANK",
            "INFY",
            "SBIN",
            "ICICIBANK",
            "ADANIENT",
            "WIPRO",
            "ITC",
            "LT",
            "AXISBANK",
            "MARUTI",
            "TITAN",
            "ULTRACEMCO",
            "BAJFINANCE",
            "ASIANPAINT",
            "TCS",
            "KOTAKBANK",
        ]

        self._calibration_map: Dict[str, float] = {}
        self._calibration_day: Optional[date] = None

    def _extract_headline(self, news_summary: str) -> str:
        try:
            for line in news_summary.split("\n"):
                if "[" in line:
                    return line.strip()[:70] + "..."
            return "Market sentiment mixed."
        except Exception:
            return "N/A"

    def _clamp(self, value: float, min_value: float, max_value: float) -> float:
        return max(min_value, min(max_value, value))

    def _is_market_hours(self) -> bool:
        now_ist = datetime.now(IST)
        if now_ist.weekday() >= 5:
            return False
        start = time(hour=9, minute=15)
        end = time(hour=15, minute=30)
        current = now_ist.time()
        return start <= current <= end

    async def _refresh_calibration_if_due(self):
        today = datetime.now(IST).date()
        if self._calibration_day == today and self._calibration_map:
            return
        calibration = await asyncio.to_thread(self._compute_calibration_map)
        self._calibration_map = calibration
        self._calibration_day = today
        logger.info("Backtest calibration refreshed for %s symbols.", len(calibration))

    def _compute_calibration_map(self) -> Dict[str, float]:
        calibration: Dict[str, float] = {}
        if yf is None:
            for symbol in self.market_watchlist:
                calibration[symbol] = 1.0
            return calibration

        for symbol in self.market_watchlist:
            try:
                ticker = f"{symbol}.NS" if not symbol.endswith(".NS") else symbol
                hist = yf.Ticker(ticker).history(period="6mo")
                if hist.empty or len(hist) < 60:
                    calibration[symbol] = 1.0
                    continue

                df = TechnicalIndicators.add_all_indicators(hist.copy())
                df["next_ret"] = df["Close"].shift(-1) / df["Close"] - 1
                strategy = df[(df["RSI"] < 45) & (df["MACD"] > df["Signal_Line"])].dropna(
                    subset=["next_ret"]
                )
                if strategy.empty:
                    calibration[symbol] = 1.0
                    continue

                win_rate = float((strategy["next_ret"] > 0).mean())
                mean_next_ret = float(strategy["next_ret"].mean())
                multiplier = 0.85 + (win_rate * 0.4) + (mean_next_ret * 4.0)
                calibration[symbol] = float(self._clamp(multiplier, 0.8, 1.3))
            except Exception:
                calibration[symbol] = 1.0
        return calibration

    def _estimate_profit_candidate(self, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        symbol = str(data.get("symbol", "")).upper()
        if not symbol:
            return None

        price = float(data.get("current_price", 0) or 0)
        if price <= 0:
            return None

        rsi = float(data.get("rsi", 50) or 50)
        volume_change_pct = float(data.get("volume_change_pct", 0) or 0)
        volatility = float(data.get("volatility_score", 0) or 0)
        trend = str(data.get("trend", "SIDEWAYS") or "SIDEWAYS").upper()

        oversold_score = self._clamp((45 - rsi) * 1.7, 0, 45) if rsi < 45 else 0
        trend_score = 28 if trend == "BULLISH" else 10 if trend == "SIDEWAYS" else 0
        volume_score = self._clamp(volume_change_pct / 5, 0, 22)
        volatility_penalty = self._clamp(volatility * 140, 0, 18)
        raw_score = float(oversold_score + trend_score + volume_score - volatility_penalty)

        calibration = self._calibration_map.get(symbol, 1.0)
        calibrated_score = int(raw_score * calibration)
        if calibrated_score < 20:
            return None

        expected_profit_pct = round(self._clamp((calibrated_score - 30) * 0.22, 0.5, 18.0), 2)
        news_analysis = self.news_bot.get_intelligence(symbol)
        headline = self._extract_headline(news_analysis)

        message = (
            f"ArthaGuard Profit Pick\n"
            f"Stock: {symbol}\n"
            f"Price: {price}\n"
            f"Profit Score: {calibrated_score}\n"
            f"Estimated Upside (heuristic): {expected_profit_pct}%\n"
            f"Signals: RSI {rsi}, Trend {trend}, Volume {volume_change_pct}%\n"
            f"Calibration Multiplier: {round(calibration, 3)}\n"
            f"News: {headline}"
        )

        return {
            "symbol": symbol,
            "alert_type": "PROFIT_PICK",
            "priority_score": calibrated_score,
            "expected_profit_pct": expected_profit_pct,
            "message": message,
        }

    async def _daily_pick_count(self, user_email: str) -> int:
        start_today = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
        return await UserActivityLog.find(
            UserActivityLog.user_email == user_email,
            UserActivityLog.action_type == self.EMAIL_LOG_ACTION,
            UserActivityLog.timestamp >= start_today,
        ).count()

    async def _symbol_already_sent_today(self, user_email: str, symbol: str) -> bool:
        start_today = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
        key = f"{self.EMAIL_LOG_ACTION}:{symbol}"
        existing = await UserActivityLog.find(
            UserActivityLog.user_email == user_email,
            UserActivityLog.action_type == key,
            UserActivityLog.timestamp >= start_today,
        ).count()
        return existing > 0

    async def _load_preferences(self) -> Dict[str, UserAlertPreference]:
        prefs = await UserAlertPreference.find_all().to_list()
        return {p.user_email: p for p in prefs}

    def _send_email_notification(self, to_email: str, subject: str, body: str):
        try:
            smtp_server = os.getenv("SMTP_SERVER", "smtp.gmail.com")
            smtp_port = int(os.getenv("SMTP_PORT", "587"))
            sender_email = os.getenv("EMAIL_SENDER")
            sender_password = os.getenv("EMAIL_PASSWORD")

            if not sender_email or not sender_password:
                logger.warning("Email sender credentials missing; skipping email.")
                return

            msg = MIMEMultipart()
            msg["From"] = sender_email
            msg["To"] = to_email
            msg["Subject"] = subject
            msg.attach(MIMEText(body, "plain"))

            server = smtplib.SMTP(smtp_server, smtp_port)
            server.starttls()
            server.login(sender_email, sender_password)
            server.send_message(msg)
            server.quit()
        except Exception as exc:
            logger.error("Email Error: %s", exc)

    async def run_monitoring_cycle(self) -> Dict[str, Any]:
        if not self._is_market_hours():
            return {"skipped": True, "reason": "outside_market_hours"}

        await self._refresh_calibration_if_due()

        market_data = await asyncio.to_thread(
            self.scanner.scan_watchlist,
            self.market_watchlist,
        )

        all_candidates: List[Dict[str, Any]] = []
        for data in market_data:
            if "error" in data:
                continue
            candidate = self._estimate_profit_candidate(data)
            if candidate:
                all_candidates.append(candidate)
        all_candidates.sort(key=lambda x: x["priority_score"], reverse=True)

        users = await User.find_all().to_list()
        prefs_map = await self._load_preferences()

        emails_sent = 0
        picks_made = 0
        for user in users:
            if not user.email:
                continue
            user_email = str(user.email)
            prefs = prefs_map.get(user_email)

            if prefs and not prefs.enabled:
                continue

            preferred_symbols = (
                set([s.upper() for s in prefs.preferred_symbols]) if prefs and prefs.preferred_symbols else None
            )
            min_profit_score = prefs.min_profit_score if prefs else self.default_min_profit_score
            min_profit_score = min(max(int(min_profit_score), 20), 90)
            daily_max_picks = prefs.daily_max_picks if prefs else self.default_daily_max_picks
            daily_max_picks = min(max(int(daily_max_picks), 5), 7)

            day_count = await self._daily_pick_count(user_email)
            if day_count >= daily_max_picks:
                continue

            user_candidates = all_candidates
            if preferred_symbols is not None:
                user_candidates = [c for c in user_candidates if c["symbol"] in preferred_symbols]
            user_candidates = [c for c in user_candidates if c["priority_score"] >= min_profit_score]
            if not user_candidates:
                continue

            best = user_candidates[0]
            if await self._symbol_already_sent_today(user_email, best["symbol"]):
                continue

            await AlertEvent(
                user_email=user_email,
                symbol=best["symbol"],
                alert_type=best["alert_type"],
                priority_score=int(best["priority_score"]),
                message=best["message"],
            ).create()

            subject = f"ArthaGuard Best Profit Pick: {best['symbol']}"
            self._send_email_notification(user_email, subject, best["message"])
            emails_sent += 1
            picks_made += 1

            now_utc = datetime.utcnow()
            await UserActivityLog(
                user_email=user_email,
                action_type=self.EMAIL_LOG_ACTION,
                timestamp=now_utc,
            ).create()
            await UserActivityLog(
                user_email=user_email,
                action_type=f"{self.EMAIL_LOG_ACTION}:{best['symbol']}",
                timestamp=now_utc,
            ).create()

        return {
            "stocks_scanned": len(market_data),
            "candidates": len(all_candidates),
            "emails_sent": emails_sent,
            "picks_made": picks_made,
        }

    async def run_forever(self):
        logger.info(
            "Alert engine started. Interval %s-%s min, daily max picks default %s.",
            self.scan_min_minutes,
            self.scan_max_minutes,
            self.default_daily_max_picks,
        )
        while True:
            try:
                report = await self.run_monitoring_cycle()
                logger.info("Alert cycle: %s", report)
            except asyncio.CancelledError:
                logger.info("Alert engine stopped.")
                raise
            except Exception as exc:
                logger.exception("Alert cycle failed: %s", exc)

            sleep_minutes = random.randint(self.scan_min_minutes, self.scan_max_minutes)
            await asyncio.sleep(sleep_minutes * 60)
