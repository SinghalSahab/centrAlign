import pytest
import uuid
from app.db import init_db, close_db, fetch_all, execute
from app.agent.permissions import PermissionManager

@pytest.mark.asyncio
async def test_recruiter_permissions():
    mgr = PermissionManager("recruiter")
    run_id = str(uuid.uuid4())
    
    # Recruiter can open ATS
    denial = await mgr.check_permission(run_id, "web_open", {"url": "/sandbox/ats/login"})
    assert denial is None

    # Recruiter can submit forms
    denial = await mgr.check_permission(run_id, "web_submit", {"form_id": "F1", "fields": {}})
    assert denial is None

    # Recruiter can message candidate
    denial = await mgr.check_permission(run_id, "message_candidate", {"applicant_id": 1, "text": "hello"})
    assert denial is None

@pytest.mark.asyncio
async def test_analyst_permissions_denial():
    await init_db()
    mgr = PermissionManager("analyst")
    run_id = str(uuid.uuid4())
    
    # Analyst cannot submit forms (read-only)
    denial = await mgr.check_permission(run_id, "web_submit", {"form_id": "F1", "fields": {"new_stage": "Shortlisted"}})
    assert denial is not None
    assert denial["error"] == "permission_denied"

    # Analyst cannot message candidate
    denial = await mgr.check_permission(run_id, "message_candidate", {"applicant_id": 1, "text": "hello"})
    assert denial is not None
    assert denial["error"] == "permission_denied"

    # Analyst cannot access Calendar app
    denial = await mgr.check_permission(run_id, "web_open", {"url": "/sandbox/calendar/login"})
    assert denial is not None
    assert denial["error"] == "permission_denied"

    # Verify audit_log table has records
    audit_rows = await fetch_all("SELECT * FROM audit_log WHERE run_id = %s", (run_id,))
    assert len(audit_rows) == 3
    assert all(r["event_type"] == "permission_denied" for r in audit_rows)

    await close_db()
