from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional

class Messenger(ABC):
    """Abstract Messenger interface standing in for WhatsApp / Telegram / Chat channels."""

    @abstractmethod
    async def send(self, recipient: str, text: str, buttons: Optional[List[Dict[str, str]]] = None) -> str:
        """
        Send an outbound message to a recipient.
        Buttons format: [{"text": "Approve", "callback_data": "approve:123"}, ...]
        Returns: external message ID as a string.
        """
        pass

    @abstractmethod
    async def wait_for_reply(self, applicant_id: int, timeout_s: int = 30) -> Optional[str]:
        """
        Wait for an inbound reply from a candidate or user.
        Returns the text message or None if timed out.
        """
        pass

    @abstractmethod
    def parse_update(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Parse incoming webhook payload into a normalized structure:
        {
            "type": "message" | "callback_query",
            "chat_id": str,
            "sender_id": str,
            "text": str,
            "callback_data": Optional[str],
            "raw": payload
        }
        """
        pass
