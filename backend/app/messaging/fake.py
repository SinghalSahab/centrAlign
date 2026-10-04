import asyncio
import logging
from typing import Any, Dict, List, Optional
from app.messaging.base import Messenger

logger = logging.getLogger("messaging.fake")

class FakeMessenger(Messenger):
    """Scripted in-memory messenger for evals, deterministic tests, and offline runs."""

    def __init__(self, scripted_replies: Optional[Dict[int, str]] = None):
        # Mapping from applicant_id -> scripted reply string
        self.scripted_replies: Dict[int, str] = scripted_replies or {
            1: "Yes, definitely interested! My notice period is 30 days and my expected CTC is 22 LPA.",
            2: "Hello! Yes, interested. My notice period is 45 days and I expect 24 LPA.",
            3: "Hi, I am interested. However, my company notice period is 90 days, and expected CTC is 25 LPA.",
            5: "Thank you for reaching out, but I have already accepted another offer and am declining this opportunity."
        }
        self.sent_messages: List[Dict[str, Any]] = []

    async def send(self, recipient: str, text: str, buttons: Optional[List[Dict[str, str]]] = None) -> str:
        msg_id = f"fake_msg_{len(self.sent_messages) + 1}"
        entry = {
            "id": msg_id,
            "recipient": recipient,
            "text": text,
            "buttons": buttons
        }
        self.sent_messages.append(entry)
        logger.info(f"FakeMessenger dispatched to {recipient}: {text[:80]}...")
        return msg_id

    async def wait_for_reply(self, applicant_id: int, timeout_s: int = 30) -> Optional[str]:
        # Return scripted reply if present
        if applicant_id in self.scripted_replies:
            reply = self.scripted_replies[applicant_id]
            logger.info(f"FakeMessenger scripted reply for applicant #{applicant_id}: {reply}")
            return reply
        return "Yes, interested! 30 days notice and 20 LPA CTC."

    def parse_update(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "type": "message",
            "chat_id": "fake_chat_1",
            "sender_id": "fake_user_1",
            "text": payload.get("text", ""),
            "callback_data": payload.get("callback_data"),
            "raw": payload
        }
