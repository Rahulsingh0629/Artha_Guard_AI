import time
import schedule
from app.database.session import SessionLocal
from app.agents.alert_engine.alert_agent import AlertAgent

# Initialize the Agent
agent = AlertAgent()

def job():
    """
    This function runs every 5 minutes.
    """
    print("\n⏰ [Worker] Starting scheduled market scan...")
    db = SessionLocal()
    try:
        # Run the analysis cycle
        report = agent.run_monitoring_cycle(db)
        
        if report['alerts_triggered'] > 0:
            print(f"✅ Scan Complete. TRIGGERED {report['alerts_triggered']} ALERTS!")
        else:
            print(f"zzz Scan Complete. No alerts triggered.")
            
    except Exception as e:
        print(f"❌ [Worker] Error during scan: {e}")
    finally:
        db.close()

# Schedule the job (e.g., every 5 minutes)
schedule.every(30).seconds.do(job)

print("🚀 ArthaGuard Alert Worker Started (Running 24/7)...")
print("Press Ctrl+C to stop.")

# The Infinite Loop
while True:
    schedule.run_pending()
    time.sleep(1)