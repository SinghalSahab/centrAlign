import asyncio
import json
import logging
import uuid
from typing import Any, Dict, List, Optional

from app.db import init_db, close_db, execute, fetch_all
from app.agent.loop import AgentLoop
from app.agent.verifier import IndependentVerifier
from app.messaging.fake import FakeMessenger
from evals.tasks import EVAL_TASKS

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("evals.runner")

async def run_single_eval(task_def: Dict[str, Any]) -> Dict[str, Any]:
    from app.main import app
    from seed import seed_all
    await seed_all()
    
    task_id = task_def["id"]
    logger.info(f"\n--- Running Eval Task: {task_def['name']} ({task_id}) ---")

    run_id = str(uuid.uuid4())
    messenger = FakeMessenger(scripted_replies=task_def.get("scripted_replies"))

    agent = AgentLoop(
        run_id=run_id,
        role_id=task_def["role"],
        task=task_def["task"],
        auto_approve=task_def.get("auto_approve", True),
        faults=task_def.get("faults", []),
        app_instance=app,
        messenger=messenger
    )

    result = await agent.run()
    steps_count = result.get("steps_count", 0)
    claims = result.get("claims", [])

    # Evaluate task specific pass/fail
    passed = False
    verified = False
    details = {}

    # Check for ask_user requirement (Task 7)
    if task_def.get("expected_tool") == "ask_user":
        # Check if ask_user step was called
        steps = await fetch_all("SELECT * FROM steps WHERE run_id = %s AND tool_name = 'ask_user'", (run_id,))
        passed = len(steps) > 0
        verified = passed
        details["ask_user_called"] = passed
    else:
        # Check claims with Independent Verifier
        verifier = IndependentVerifier()
        if claims:
            v_report = await verifier.verify_claims(run_id, claims)
            verified = v_report["all_passed"]
            passed = verified and result.get("status") == "completed"
            details["verifier_report"] = v_report
        else:
            # Fallback for error/status check
            passed = result.get("status") in ["completed", "needs_user"]
            verified = False

    # Count retries (steps with recovery actions)
    retries = await fetch_all("SELECT COUNT(*) as count FROM steps WHERE run_id = %s AND recovery_action IS NOT NULL", (run_id,))
    retries_count = retries[0]["count"] if retries else 0

    # Record eval result in database
    await execute(
        """INSERT INTO eval_results (task_id, run_id, passed, steps_count, retries_count, verified, details)
           VALUES (%s, %s, %s, %s, %s, %s, %s)""",
        (task_id, run_id, passed, steps_count, retries_count, verified, details)
    )

    eval_summary = {
        "task_id": task_id,
        "name": task_def["name"],
        "run_id": run_id,
        "passed": passed,
        "verified": verified,
        "steps_count": steps_count,
        "retries_count": retries_count,
        "details": details
    }
    logger.info(f"Task {task_id} result: Passed={passed}, Verified={verified}, Steps={steps_count}")
    return eval_summary

async def run_all_evals() -> Dict[str, Any]:
    await init_db()
    results = []

    for t in EVAL_TASKS:
        # Reset DB seed between certain destructive evals if needed
        try:
            summary = await run_single_eval(t)
            results.append(summary)
        except Exception as e:
            logger.error(f"Task {t['id']} threw exception: {e}", exc_info=True)
            results.append({
                "task_id": t["id"],
                "name": t["name"],
                "passed": False,
                "verified": False,
                "error": str(e)
            })

    total = len(results)
    passed_count = sum(1 for r in results if r.get("passed"))
    verified_count = sum(1 for r in results if r.get("verified"))
    avg_steps = sum(r.get("steps_count", 0) for r in results) / max(total, 1)

    benchmark = {
        "total_tasks": total,
        "passed_tasks": passed_count,
        "success_rate": round(passed_count / max(total, 1) * 100, 1),
        "verified_tasks": verified_count,
        "verification_accuracy": round(verified_count / max(total, 1) * 100, 1),
        "average_steps": round(avg_steps, 1),
        "results": results
    }

    print("\n" + "=" * 60)
    print("EVALUATION BENCHMARK SUITE RESULTS")
    print("=" * 60)
    print(f"Total Tasks: {benchmark['total_tasks']}")
    print(f"Passed: {benchmark['passed_tasks']} ({benchmark['success_rate']}%)")
    print(f"Verified: {benchmark['verified_tasks']} ({benchmark['verification_accuracy']}%)")
    print(f"Average Steps: {benchmark['average_steps']}")
    print("-" * 60)
    for r in results:
        status_sym = "✓ PASS" if r.get("passed") else "✗ FAIL"
        print(f"{status_sym} [{r.get('task_id')}]: {r.get('name')} (Steps: {r.get('steps_count', 0)})")
    print("=" * 60)

    await close_db()
    return benchmark

if __name__ == "__main__":
    asyncio.run(run_all_evals())
