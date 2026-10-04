import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.config import settings
from app.db import init_db, close_db, fetch_one
from app.sandbox.ats.router import router as ats_router
from app.sandbox.calendar.router import router as cal_router
from app.api.runs import router as runs_router
from app.api.evals import router as evals_router
from app.api.telegram import router as telegram_router
from app.messaging.telegram import TelegramMessenger

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("main")

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Initializing CentrAlign backend services...")
    await init_db()
    # Check if database has jobs seeded, if not run seed
    try:
        job = await fetch_one("SELECT id FROM jobs LIMIT 1")
        if not job:
            logger.info("Database empty, running automated seed...")
            from seed import seed_all
            await seed_all()
    except Exception as e:
        logger.warning(f"Seed check error: {e}")

    # Register Telegram webhook on startup if token is configured
    if settings.TELEGRAM_BOT_TOKEN and not settings.TELEGRAM_BOT_TOKEN.startswith("your_"):
        webhook_url = f"{settings.SANDBOX_BASE_URL.rstrip('/')}/api/telegram/webhook"
        logger.info(f"Attempting to register Telegram webhook: {webhook_url}")
        messenger = TelegramMessenger()
        await messenger.register_webhook(webhook_url, settings.TELEGRAM_WEBHOOK_SECRET)

    yield
    logger.info("Shutting down CentrAlign backend services...")
    await close_db()

app = FastAPI(
    title="CentrAlign Autonomous AI Worker Platform",
    description="Generic agent runtime with sandbox ATS & Calendar, verification, and human escalation.",
    version="1.0.0",
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount Routers
app.include_router(ats_router)
app.include_router(cal_router)
app.include_router(runs_router)
app.include_router(evals_router)
app.include_router(telegram_router)


@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "service": "CentrAlign AI Platform",
        "database": "connected",
        "gemini_model": settings.GEMINI_MODEL
    }

@app.get("/")
async def root():
    return {
        "message": "Welcome to CentrAlign AI Platform Prototype",
        "endpoints": {
            "health": "/health",
            "ats_sandbox": "/sandbox/ats/",
            "calendar_sandbox": "/sandbox/calendar/",
            "runs": "/api/runs",
            "evals": "/api/evals"
        }
    }
