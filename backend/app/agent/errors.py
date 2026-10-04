import re
from typing import Optional, Tuple

class ErrorClassifier:
    """Classifies errors into standardized categories and recommends recovery actions."""

    TRANSIENT = "transient"
    SELECTOR_MISSING = "selector_missing"
    AUTH_EXPIRED = "auth_expired"
    VALIDATION = "validation"
    SLOT_CONFLICT = "slot_conflict"
    NO_REPLY = "no_reply"
    PERMISSION_DENIED = "permission_denied"
    DUPLICATE = "duplicate"
    UNKNOWN = "unknown"

    @classmethod
    def classify(cls, error_msg: str, status_code: Optional[int] = None) -> Tuple[str, str]:
        """
        Returns (category, suggested_recovery_strategy).
        """
        msg = (error_msg or "").lower()

        # Status code fast paths
        if status_code in (401, 403) or "unauthorized" in msg or "session expired" in msg or "log in again" in msg:
            return cls.AUTH_EXPIRED, "Fetch credentials via get_credentials and log in again."

        if status_code in (502, 503, 504, 500) or "flaky" in msg or "timeout" in msg or "connection reset" in msg:
            return cls.TRANSIENT, "Perform exponential backoff and retry the operation (up to 2 times)."

        if "permission_denied" in msg or "not permitted" in msg or "strictly read-only" in msg:
            return cls.PERMISSION_DENIED, "Do not attempt workarounds. Escalate or report required permissions."

        if "slot conflict" in msg or "already booked" in msg or "taken by another" in msg:
            return cls.SLOT_CONFLICT, "Re-read the calendar overview and select the next available free slot."

        if "validation" in msg or "numeric" in msg or "parse" in msg:
            return cls.VALIDATION, "Inspect validation error message and reformat input to expected type (e.g. numeric LPA)."

        if "not found" in msg or "link '" in msg or "form '" in msg:
            return cls.SELECTOR_MISSING, "Call web_read to inspect current DOM, locate updated element ID, and re-plan."

        if "no reply" in msg or "timed out waiting for reply" in msg:
            return cls.NO_REPLY, "Send one polite follow-up nudge, or mark candidate uncontactable."

        if "duplicate" in msg or "already exists" in msg or "already has an interview" in msg:
            return cls.DUPLICATE, "Halt redundant creation; record existing status."

        return cls.UNKNOWN, "Review page content and adapt plan, or call ask_user if ambiguous."
