from app.database.session import SessionLocal
from app.agents.alert_engine.alert_agent import AlertAgent

def run_once():
    db = SessionLocal()
    try:
        agent = AlertAgent()
        agent.run_monitoring_cycle(db)
        print("✅ Alert scan completed")
    except Exception as e:
        print("❌ Worker error:", e)
    finally:
        db.close()

if __name__ == "__main__":
    run_once()
