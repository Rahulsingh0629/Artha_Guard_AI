import asyncio
import importlib
import logging

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.auth import auth_router
from app.database.mongodb import init_db

load_dotenv(dotenv_path=".env")
logger = logging.getLogger("Main")


app = FastAPI(
    title="ArthaGuard AI",
    description="AI for Financial Markets",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def _try_include_router(module_path: str, prefix: str, tags: list[str]):
    try:
        mod = importlib.import_module(module_path)
        router = getattr(mod, "router", None)
        if router is None:
            logger.warning("Router missing in module %s", module_path)
            return
        app.include_router(router, prefix=prefix, tags=tags)
        logger.info("Included router %s", module_path)
    except Exception as exc:
        logger.warning("Skipped router %s due to import error: %s", module_path, exc)


@app.on_event("startup")
async def start_services():
    await init_db()
    logger.info("Connected to MongoDB successfully.")

    # Optional background alert engine. Do not block API if optional deps are missing.
    try:
        alert_mod = importlib.import_module("app.agents.alert_engine.alert_agent")
        alert_agent_cls = getattr(alert_mod, "AlertAgent")
        app.state.alert_agent = alert_agent_cls()
        app.state.alert_task = asyncio.create_task(app.state.alert_agent.run_forever())
        logger.info("Background alert engine started.")
    except Exception as exc:
        logger.warning("Alert engine disabled due to startup error: %s", exc)


@app.on_event("shutdown")
async def stop_services():
    task = getattr(app.state, "alert_task", None)
    if task and not task.done():
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass
    logger.info("Background alert engine stopped.")


app.include_router(auth_router.router, prefix="/api/v1/auth", tags=["Authentication"])
_try_include_router("app.api.portfolio_routes", "/api/v1/portfolio", ["Portfolio"])
_try_include_router("app.api.news_routes", "/api/v1/news", ["News"])
_try_include_router("app.api.scanner_routes", "/api/v1/scanner", ["Scanner"])
_try_include_router("app.api.advisory_routes", "/api/v1/advisory", ["Advisory Agent"])
_try_include_router("app.api.fraud_routes", "/api/v1/fraud", ["Fraud Agent"])
_try_include_router("app.api.market_routes", "/api/v1/market", ["Market"])
_try_include_router("app.api.alert_routes", "/api/v1/alerts", ["Alerts"])


@app.get("/")
def read_root():
    return {
        "project": "ArthaGuard AI",
        "status": "active",
        "message": "Backend is running. Optional modules load when dependencies are present.",
    }
