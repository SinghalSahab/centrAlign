import asyncio
import json
import uuid
import sys
from app.db import init_db, close_db, fetch_one, fetch_all
from app.main import app
from app.agent.loop import AgentLoop

async def main():
    print("=" * 60)
    print("CentrAlign CLI Runner - Happy Path Execution")
    print("=" * 60)
    
    await init_db()

    run_id = str(uuid.uuid4())
    task = (
        "We're hiring a Backend Engineer. Review the applicants against our hiring rubric, "
        "shortlist the best two, confirm their interest, notice period and expected CTC on Telegram, "
        "and book interviews with the hiring manager for those who qualify. Update the ATS and tell me when it's done."
    )

    print(f"Run ID: {run_id}")
    print(f"Task: {task}\n")

    def on_step(step):
        action = step.get("action_type")
        tool = step.get("tool_name")
        num = step.get("step_number")
        print(f"[Step {num}] {action.upper()} -> {tool or ''}")
        if step.get("observation"):
            obs_preview = step['observation'].replace('\n', ' ')[:120]
            print(f"         Result: {obs_preview}...")

    agent = AgentLoop(
        run_id=run_id,
        role_id="recruiter",
        task=task,
        auto_approve=True,
        faults=[],
        app_instance=app,
        step_callback=on_step
    )

    result = await agent.run()
    print("\n" + "=" * 60)
    print("AGENT RUN COMPLETED")
    print("=" * 60)
    print(f"Status: {result.get('status')}")
    print(f"Steps count: {result.get('steps_count')}")
    print(f"Summary: {result.get('summary')}")
    print("\nClaims:")
    for c in result.get("claims", []):
        print(f" - {c.get('type')}: {c.get('details')}")

    # Inspect Sandbox Database State
    print("\n" + "=" * 60)
    print("GROUND TRUTH VERIFICATION PREVIEW (DATABASE STATE)")
    print("=" * 60)
    applicant = await fetch_one("SELECT * FROM applicants WHERE id = 1")
    print(f"Applicant #1 Stage: {applicant.get('stage')}")
    print(f"Applicant #1 Intent: interested={applicant.get('interested')}, notice={applicant.get('notice_period_days')}d, CTC={applicant.get('expected_ctc_lpa')} LPA")
    
    interview = await fetch_one("SELECT * FROM interviews WHERE applicant_id = 1")
    print(f"Interview Record: {interview}")
    
    slot = await fetch_one("SELECT * FROM slots WHERE id = 1")
    print(f"Slot #1 Booked By: Applicant #{slot.get('booked_applicant_id')}")

    await close_db()

if __name__ == "__main__":
    asyncio.run(main())
