import asyncio
import json
import logging
import uuid
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, BackgroundTasks, Header, HTTPException, Request, Response
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from app.config import settings
from app.db import fetch_one, fetch_all, execute
from app.agent.loop import AgentLoop
from app.agent.verifier import IndependentVerifier
from app.messaging.telegram import TelegramMessenger

logger = logging.getLogger("api.runs")
router = APIRouter(prefix="/api/runs", tags=["Runs"])

class RunCreateRequest(BaseModel):
    role: str = "recruiter"
    task: str
    faults: List[str] = []
    auto_approve: bool = True

class SSEManager:
    def __init__(self):
        self.listeners: Dict[str, List[asyncio.Queue]] = {}

    def subscribe(self, run_id: str) -> asyncio.Queue:
        q = asyncio.Queue()
        self.listeners.setdefault(run_id, []).append(q)
        return q

    def unsubscribe(self, run_id: str, q: asyncio.Queue):
        if run_id in self.listeners and q in self.listeners[run_id]:
            self.listeners[run_id].remove(q)

    async def broadcast(self, run_id: str, event_type: str, data: Any):
        if run_id in self.listeners:
            msg = f"event: {event_type}\ndata: {json.dumps(data)}\n\n"
            for q in self.listeners[run_id]:
                await q.put(msg)

sse_manager = SSEManager()
_active_agent_loops: Dict[str, AgentLoop] = {}

async def _run_agent_task(run_id: str, role: str, task: str, faults: List[str], auto_approve: bool):
    from app.main import app # local import to avoid circular dependency
    messenger = TelegramMessenger()

    def on_step(step_data: Dict[str, Any]):
        asyncio.create_task(sse_manager.broadcast(run_id, "step", step_data))

    agent = AgentLoop(
        run_id=run_id,
        role_id=role,
        task=task,
        auto_approve=auto_approve,
        faults=faults,
        app_instance=app,
        messenger=messenger,
        step_callback=on_step
    )
    _active_agent_loops[run_id] = agent

    try:
        result = await agent.run()
        
        # If run completed, execute independent verifier!
        if result.get("status") == "completed" and result.get("claims"):
            verifier = IndependentVerifier()
            verification_report = await verifier.verify_claims(run_id, result["claims"])
            
            # Save verification result to run or eval table
            await execute(
                "UPDATE runs SET error = %s WHERE id = %s",
                (json.dumps(verification_report), run_id)
            )
            result["verification"] = verification_report
            await sse_manager.broadcast(run_id, "verified", verification_report)

        await sse_manager.broadcast(run_id, "completed", result)
    except Exception as e:
        logger.error(f"Error in background agent run {run_id}: {e}", exc_info=True)
        await execute("UPDATE runs SET status = 'failed', error = %s WHERE id = %s", (str(e), run_id))
        await sse_manager.broadcast(run_id, "error", {"error": str(e)})
    finally:
        _active_agent_loops.pop(run_id, None)

@router.post("")
async def create_run(
    req: RunCreateRequest,
    background_tasks: BackgroundTasks,
    x_admin_token: Optional[str] = Header(None)
):
    # Protect against strangers burning quota if admin token is configured
    if settings.ADMIN_TOKEN and settings.ADMIN_TOKEN != "demo-admin-secret-token":
        if x_admin_token != settings.ADMIN_TOKEN:
            raise HTTPException(status_code=403, detail="Invalid admin authorization token")

    run_id = str(uuid.uuid4())
    await execute(
        """INSERT INTO runs (id, role, task, status, faults, auto_approve)
           VALUES (%s, %s, %s, 'running', %s, %s)""",
        (run_id, req.role.lower(), req.task, req.faults, req.auto_approve)
    )

    background_tasks.add_task(
        _run_agent_task,
        run_id,
        req.role.lower(),
        req.task,
        req.faults,
        req.auto_approve
    )

    return {"run_id": run_id, "status": "running", "role": req.role}

@router.get("")
async def list_runs(limit: int = 20):
    rows = await fetch_all(
        "SELECT id, role, task, status, created_at, completed_at, summary FROM runs ORDER BY created_at DESC LIMIT %s",
        (limit,)
    )
    return {"runs": rows}

@router.get("/{run_id}")
async def get_run_detail(run_id: str):
    run = await fetch_one("SELECT * FROM runs WHERE id = %s", (run_id,))
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")

    steps = await fetch_all("SELECT * FROM steps WHERE run_id = %s ORDER BY step_number ASC", (run_id,))
    facts = await fetch_all("SELECT key, value, source, created_at FROM memory_facts WHERE run_id = %s ORDER BY id ASC", (run_id,))
    approvals = await fetch_all("SELECT * FROM approvals WHERE run_id = %s ORDER BY id ASC", (run_id,))
    audit_logs = await fetch_all("SELECT * FROM audit_log WHERE run_id = %s ORDER BY id ASC", (run_id,))
    messages = await fetch_all("SELECT * FROM messages WHERE run_id = %s ORDER BY id ASC", (run_id,))

    # Parse verification details if present
    verification = None
    if run.get("error") and run["error"].startswith("{"):
        try:
            verification = json.loads(run["error"])
        except Exception:
            pass

    return {
        "run": run,
        "verification": verification,
        "steps": steps,
        "memory_facts": facts,
        "approvals": approvals,
        "audit_logs": audit_logs,
        "messages": messages
    }

@router.get("/{run_id}/events")
async def stream_run_events(run_id: str):
    """SSE endpoint streaming live agent steps, thoughts, errors, and verification badges."""
    queue = sse_manager.subscribe(run_id)

    async def event_generator():
        try:
            # Yield initial connection heartbeat
            yield f"event: connected\ndata: {json.dumps({'run_id': run_id})}\n\n"

            # Replay existing steps
            existing_steps = await fetch_all("SELECT * FROM steps WHERE run_id = %s ORDER BY step_number ASC", (run_id,))
            for s in existing_steps:
                yield f"event: step\ndata: {json.dumps(s)}\n\n"

            while True:
                # Wait for next event or send heartbeat
                try:
                    msg = await asyncio.wait_for(queue.get(), timeout=15.0)
                    yield msg
                except asyncio.TimeoutError:
                    yield ": heartbeat\n\n"
        except asyncio.CancelledError:
            pass
        finally:
            sse_manager.unsubscribe(run_id, queue)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )

@router.post("/{run_id}/approve")
async def approve_run_action(run_id: str, payload: Dict[str, Any]):
    approval_id = payload.get("approval_id")
    decision = payload.get("decision", "approved") # approved or rejected

    await execute(
        "UPDATE approvals SET status = %s, decided_at = CURRENT_TIMESTAMP WHERE id = %s",
        (decision, approval_id)
    )
    await execute("UPDATE runs SET status = 'running' WHERE id = %s", (run_id,))

    await sse_manager.broadcast(run_id, "approval_decision", {"approval_id": approval_id, "decision": decision})
    return {"status": "ok", "decision": decision}

@router.post("/{run_id}/reply")
async def reply_to_run(run_id: str, payload: Dict[str, Any]):
    user_reply = payload.get("reply", "")
    agent = _active_agent_loops.get(run_id)
    if agent:
        agent.history.append({"role": "user", "content": f"[USER CLARIFICATION]: {user_reply}"})
    await execute("UPDATE runs SET status = 'running' WHERE id = %s", (run_id,))
    await sse_manager.broadcast(run_id, "user_reply", {"reply": user_reply})
    return {"status": "ok", "message": "Reply recorded"}
