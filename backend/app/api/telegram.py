import logging
from typing import Any, Dict
from fastapi import APIRouter, Header, HTTPException, Request

from app.config import settings
from app.db import execute, fetch_one
from app.messaging.telegram import TelegramMessenger

logger = logging.getLogger("api.telegram")
router = APIRouter(prefix="/api/telegram", tags=["Telegram Webhook"])

messenger = TelegramMessenger()

@router.post("/webhook")
async def telegram_webhook(
    request: Request,
    x_telegram_bot_api_secret_token: str = Header(None)
):
    # Validate secret token if configured
    if settings.TELEGRAM_WEBHOOK_SECRET and settings.TELEGRAM_WEBHOOK_SECRET != "default_secret":
        if x_telegram_bot_api_secret_token != settings.TELEGRAM_WEBHOOK_SECRET:
            raise HTTPException(status_code=403, detail="Invalid Telegram webhook secret")

    payload = await request.json()
    logger.info(f"Incoming Telegram webhook: {payload}")
    update = messenger.parse_update(payload)

    # 1. Handle Inline Button Approval / Rejection
    if update["type"] == "callback_query" and update.get("callback_data"):
        data = update["callback_data"]
        if data.startswith("approve:"):
            approval_id = int(data.split(":")[1])
            await execute(
                "UPDATE approvals SET status = 'approved', decided_at = CURRENT_TIMESTAMP WHERE id = %s",
                (approval_id,)
            )
            # Find associated run
            appr = await fetch_one("SELECT run_id FROM approvals WHERE id = %s", (approval_id,))
            if appr:
                await execute("UPDATE runs SET status = 'running' WHERE id = %s", (appr["run_id"],))
            return {"status": "ok", "action": "approved"}
        elif data.startswith("reject:"):
            approval_id = int(data.split(":")[1])
            await execute(
                "UPDATE approvals SET status = 'rejected', decided_at = CURRENT_TIMESTAMP WHERE id = %s",
                (approval_id,)
            )
            return {"status": "ok", "action": "rejected"}

    # 2. Handle Inbound Candidate Chat Messages
    if update["type"] == "message":
        text = update.get("text", "")
        # Record message in messages table
        await execute(
            "INSERT INTO messages (direction, text, external_id) VALUES ('inbound', %s, %s)",
            (text, update.get("chat_id"))
        )
        # Check pending waits
        pending = await fetch_one("SELECT * FROM pending_waits ORDER BY id DESC LIMIT 1")
        if pending:
            run_id = pending["run_id"]
            await execute("DELETE FROM pending_waits WHERE id = %s", (pending["id"],))
            await execute("UPDATE runs SET status = 'running' WHERE id = %s", (run_id,))
            logger.info(f"Resumed pending wait for run {run_id} via incoming candidate message.")

    return {"status": "ok"}
