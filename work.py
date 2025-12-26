"""
ArthaGuard Alert Worker
Runs ONE alert scan cycle.
Designed for GitHub Actions / Cron execution.
"""

from app.database.session import SessionLocal
from app.agents.alert_engine.alert_agent import AlertAgent

def run_once():
    print("⏰ [Worker] Starting alert scan...")
    db = SessionLocal()
    try:
        agent = AlertAgent()
        report = agent.run_monitoring_cycle(db)

        print("✅ Alert scan completed")
        print(report)

    except Exception as e:
        print("❌ Worker error:", e)

    finally:
        db.close()

if __name__ == "__main__":
    run_once()
