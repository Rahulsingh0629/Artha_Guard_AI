"""
ArthaGuard Alert Worker
Runs ONE alert scan cycle.
Designed for GitHub Actions / Cron execution.
"""
import asyncio
import logging
from app.database.mongodb import init_db
from app.agents.alert_engine.alert_agent import AlertAgent

# Setup Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("Worker")

async def run_once():
    print("⏰ [Worker] Starting alert scan...")
    
    # 1. Connect to MongoDB (Required for Beanie)
    try:
        await init_db()
        
        # 2. Initialize Agent
        agent = AlertAgent()
        
        # 3. Run Cycle (Async)
        # Note: We no longer pass 'db' because MongoDB handles connections internally
        report = await agent.run_monitoring_cycle()

        print("✅ Alert scan completed")
        print(report)

    except Exception as e:
        print("❌ Worker error:", e)

if __name__ == "__main__":
    # Run the async function
    asyncio.run(run_once())