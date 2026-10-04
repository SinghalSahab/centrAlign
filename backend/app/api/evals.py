import logging
from typing import Any, Dict
from fastapi import APIRouter, BackgroundTasks

from app.db import fetch_all
from evals.runner import run_all_evals
from evals.tasks import EVAL_TASKS

logger = logging.getLogger("api.evals")
router = APIRouter(prefix="/api/evals", tags=["Evaluations"])

@router.get("")
async def get_evals_summary():
    """Retrieve historical eval benchmarks and task suite definitions."""
    results = await fetch_all(
        "SELECT * FROM eval_results ORDER BY created_at DESC LIMIT 50"
    )
    
    total = len(results)
    passed = sum(1 for r in results if r.get("passed"))
    verified = sum(1 for r in results if r.get("verified"))
    avg_steps = (sum(r.get("steps_count", 0) for r in results) / max(total, 1)) if total > 0 else 0

    return {
        "benchmark_summary": {
            "total_runs": total,
            "passed_runs": passed,
            "success_rate": round(passed / max(total, 1) * 100, 1) if total > 0 else 0,
            "verification_accuracy": round(verified / max(total, 1) * 100, 1) if total > 0 else 0,
            "average_steps": round(avg_steps, 1)
        },
        "tasks": EVAL_TASKS,
        "recent_results": results
    }

@router.post("/run")
async def trigger_evals(background_tasks: BackgroundTasks):
    """Trigger the 8-task evaluation benchmark suite."""
    logger.info("Triggering full evaluation benchmark suite...")
    # Run inline or in background
    results = await run_all_evals()
    return {"status": "completed", "benchmark": results}
