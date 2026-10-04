import logging
from pathlib import Path
from typing import Any, Dict, List, Optional
import yaml
from app.db import execute

logger = logging.getLogger("agent.permissions")

class PermissionManager:
    """Enforces role-based permissions before any tool execution."""

    def __init__(self, role_id: str):
        self.role_id = role_id.lower()
        self.config = self._load_role_config(self.role_id)
        self.allowed_tools: List[str] = self.config.get("allowed_tools", [])
        self.allowed_apps: List[str] = self.config.get("allowed_apps", [])
        self.write_tools_require_approval: bool = self.config.get("write_tools_require_approval", True)

    def _load_role_config(self, role_id: str) -> Dict[str, Any]:
        roles_dir = Path(__file__).resolve().parent.parent / "roles"
        file_path = roles_dir / f"{role_id}.yaml"
        if not file_path.exists():
            raise ValueError(f"Role configuration not found for '{role_id}' at {file_path}")
        with open(file_path, "r", encoding="utf-8") as f:
            return yaml.safe_load(f)

    async def check_permission(self, run_id: str, tool_name: str, tool_args: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Validates if tool_name and args are permitted.
        Returns None if permitted.
        Returns a dict with error 'permission_denied' and explanation if denied, and logs to audit_log.
        """
        role_name = self.config.get("name", self.role_id)

        # 1. Check if tool is allowed
        if tool_name not in self.allowed_tools:
            reason = f"Role '{role_name}' is not permitted to use tool '{tool_name}'. Allowed tools: {', '.join(self.allowed_tools)}"
            await self._log_audit(run_id, "permission_denied", tool_name, tool_args, reason)
            return {"status": "error", "error": "permission_denied", "message": reason}

        # 2. Check App access for web tools
        target_path = None
        if tool_name == "web_open":
            target_path = tool_args.get("url", "")
        elif tool_name == "get_credentials":
            app = tool_args.get("app", "")
            if app and app.lower() not in [a.lower() for a in self.allowed_apps]:
                reason = f"Role '{role_name}' is not permitted to access credentials for app '{app}'. Allowed apps: {', '.join(self.allowed_apps)}"
                await self._log_audit(run_id, "permission_denied", tool_name, tool_args, reason)
                return {"status": "error", "error": "permission_denied", "message": reason}

        if target_path:
            if "/sandbox/calendar" in target_path and "calendar" not in [a.lower() for a in self.allowed_apps]:
                reason = f"Role '{role_name}' is not permitted to access the Calendar application."
                await self._log_audit(run_id, "permission_denied", tool_name, tool_args, reason)
                return {"status": "error", "error": "permission_denied", "message": reason}
            if "/sandbox/ats" in target_path and "ats" not in [a.lower() for a in self.allowed_apps]:
                reason = f"Role '{role_name}' is not permitted to access the ATS application."
                await self._log_audit(run_id, "permission_denied", tool_name, tool_args, reason)
                return {"status": "error", "error": "permission_denied", "message": reason}

        # 3. Check write tool restrictions
        if self.role_id == "analyst":
            if tool_name == "web_submit":
                reason = f"Role '{role_name}' is strictly read-only and cannot submit form modifications."
                await self._log_audit(run_id, "permission_denied", tool_name, tool_args, reason)
                return {"status": "error", "error": "permission_denied", "message": reason}

        return None

    async def _log_audit(self, run_id: str, event_type: str, tool_name: str, tool_args: Dict[str, Any], reason: str):
        details = {
            "role": self.role_id,
            "tool_name": tool_name,
            "tool_args": tool_args,
            "reason": reason
        }
        await execute(
            "INSERT INTO audit_log (run_id, event_type, details) VALUES (%s, %s, %s)",
            (run_id, event_type, details)
        )
        logger.warning(f"Audit Log [{event_type}] for run {run_id}: {reason}")
