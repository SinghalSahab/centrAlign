import pytest
import uuid
from app.db import init_db, close_db, execute
from app.agent.verifier import IndependentVerifier

@pytest.mark.asyncio
async def test_verifier_checks():
    await init_db()
    verifier = IndependentVerifier()
    run_id = str(uuid.uuid4())

    # 1. Shortlist valid check
    valid_res = await verifier.verify_claims(run_id, [
        {"type": "shortlist_valid", "details": {"job_id": 1, "applicant_ids": [1, 2]}}
    ])
    assert valid_res["all_passed"] is True

    # Invalid shortlist (contains candidate not in expected ground truth)
    invalid_res = await verifier.verify_claims(run_id, [
        {"type": "shortlist_valid", "details": {"job_id": 1, "applicant_ids": [4]}} # Vikram is not in expected
    ])
    assert invalid_res["all_passed"] is False

    # 2. Stage check
    stage_res = await verifier.verify_claims(run_id, [
        {"type": "stage_is", "details": {"applicant_id": 2, "stage": "Applied"}}
    ])
    assert stage_res["all_passed"] is True

    # 3. Policy respected check for 90-day notice candidate (Applicant #3)
    # Rohan Verma has 90-day notice period. If no interview is booked, policy is respected.
    pol_res = await verifier.verify_claims(run_id, [
        {"type": "policy_respected", "details": {"applicant_id": 3, "max_notice_days": 60}}
    ])
    assert pol_res["all_passed"] is True

    # 4. Unknown claim type
    unk_res = await verifier.verify_claims(run_id, [
        {"type": "unsupported_claim_xyz", "details": {}}
    ])
    assert unk_res["all_passed"] is False
    assert "Unverifiable" in unk_res["check_results"][0]["error"]

    await close_db()
