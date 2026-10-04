import json
import logging
from typing import Any, Dict, List, Optional
from app.db import fetch_one, fetch_all, execute

logger = logging.getLogger("agent.memory")

class MemoryManager:
    """Manages per-run scratchpad, key-value memory facts, and rolling summary."""

    def __init__(self, run_id: str):
        self.run_id = run_id
        self._cached_facts: Dict[str, Any] = {}
        self._rolling_summary: str = ""

    async def write(self, key: str, value: Any, source: str = "agent") -> str:
        """Write a fact to company memory and database."""
        self._cached_facts[key] = value
        val_json = json.dumps(value) if not isinstance(value, str) else value
        
        # Check if fact already exists
        existing = await fetch_one(
            "SELECT id FROM memory_facts WHERE run_id = %s AND key = %s",
            (self.run_id, key)
        )
        if existing:
            await execute(
                "UPDATE memory_facts SET value = %s, source = %s WHERE id = %s",
                (val_json, source, existing["id"])
            )
        else:
            await execute(
                "INSERT INTO memory_facts (run_id, key, value, source) VALUES (%s, %s, %s, %s)",
                (self.run_id, key, val_json, source)
            )
        logger.info(f"Memory saved [{key}]: {val_json[:100]}")
        return f"Successfully saved memory fact '{key}'."

    async def read(self, key: str) -> Optional[Any]:
        """Read a fact from company memory."""
        if key in self._cached_facts:
            return self._cached_facts[key]
        
        row = await fetch_one(
            "SELECT value FROM memory_facts WHERE run_id = %s AND key = %s",
            (self.run_id, key)
        )
        if row:
            val = row["value"]
            if isinstance(val, str) and (val.startswith("{") or val.startswith("[")):
                try:
                    val = json.loads(val)
                except Exception:
                    pass
            self._cached_facts[key] = val
            return val
        return None

    async def get_all_facts(self) -> Dict[str, Any]:
        rows = await fetch_all(
            "SELECT key, value FROM memory_facts WHERE run_id = %s ORDER BY id ASC",
            (self.run_id,)
        )
        facts = {}
        for r in rows:
            val = r["value"]
            if isinstance(val, str) and (val.startswith("{") or val.startswith("[")):
                try:
                    val = json.loads(val)
                except Exception:
                    pass
            facts[r["key"]] = val
        self._cached_facts.update(facts)
        return self._cached_facts

    async def set_summary(self, summary: str):
        self._rolling_summary = summary
        await execute("UPDATE runs SET summary = %s WHERE id = %s", (summary, self.run_id))

    async def get_summary(self) -> str:
        if self._rolling_summary:
            return self._rolling_summary
        row = await fetch_one("SELECT summary FROM runs WHERE id = %s", (self.run_id,))
        if row and row.get("summary"):
            self._rolling_summary = row["summary"]
        return self._rolling_summary

    async def format_memory_context(self) -> str:
        facts = await self.get_all_facts()
        if not facts:
            return "Current Memory: (No facts recorded yet)"
        
        lines = ["Current Run Memory / Scratchpad:"]
        for k, v in facts.items():
            if isinstance(v, (dict, list)):
                lines.append(f"- {k}: {json.dumps(v)}")
            else:
                lines.append(f"- {k}: {v}")
        return "\n".join(lines)
