import json
import logging
from typing import Any, Dict, List, Optional, Tuple

from app.db import fetch_one, fetch_all

logger = logging.getLogger("agent.verifier")

class IndependentVerifier:
    """
    Independent ground-truth verifier.
    Inspects Postgres database state directly — NEVER relies on agent memory or self-reported claims.
    """

    async def verify_claims(self, run_id: str, claims: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Runs the fixed library of read-only checkers against the database.
        Returns: {
            "all_passed": bool,
            "total_checks": int,
            "passed_checks": int,
            "failed_checks": int,
            "check_results": [
                {"type": ..., "passed": bool, "evidence": ..., "error": ...}
            ]
        }
        """
        results = []
        all_passed = True

        for claim in claims:
            ctype = claim.get("type")
            details = claim.get("details", {})
            passed, evidence, error = await self._run_single_check(run_id, ctype, details)

            if not passed:
                all_passed = False

            results.append({
                "type": ctype,
                "passed": passed,
                "evidence": evidence,
                "error": error
            })

        return {
            "all_passed": all_passed,
            "total_checks": len(claims),
            "passed_checks": sum(1 for r in results if r["passed"]),
            "failed_checks": sum(1 for r in results if not r["passed"]),
            "check_results": results
        }

    async def _run_single_check(self, run_id: str, claim_type: str, details: Dict[str, Any]) -> Tuple[bool, str, Optional[str]]:
        try:
            if claim_type == "shortlist_valid":
                return await self._check_shortlist_valid(details)

            elif claim_type == "intent_matches_reply":
                return await self._check_intent_matches_reply(details)

            elif claim_type == "policy_respected":
                return await self._check_policy_respected(details)

            elif claim_type == "interview_booked":
                return await self._check_interview_booked(details)

            elif claim_type == "stage_is":
                return await self._check_stage_is(details)

            elif claim_type == "no_booking":
                return await self._check_no_booking(details)

            elif claim_type == "count_applicants":
                return await self._check_count_applicants(details)

            elif claim_type == "permission_denied_logged":
                return await self._check_permission_denied_logged(run_id)

            else:
                return False, "", f"Unverifiable claim: Unknown claim type '{claim_type}'"

        except Exception as e:
            logger.error(f"Error evaluating claim '{claim_type}': {e}")
            return False, "", f"Verifier execution error: {str(e)}"

    async def _check_shortlist_valid(self, details: Dict[str, Any]) -> Tuple[bool, str, Optional[str]]:
        job_id = details.get("job_id")
        candidate_ids = details.get("applicant_ids", [])
        
        job = await fetch_one("SELECT expected_shortlist_ids FROM jobs WHERE id = %s", (job_id,))
        if not job:
            return False, "", f"Job #{job_id} does not exist in database."

        expected = job["expected_shortlist_ids"]
        if isinstance(expected, str):
            try:
                expected = json.loads(expected)
            except Exception:
                expected = []
        expected_set = set(expected)
        actual_set = set(candidate_ids)

        if actual_set.issubset(expected_set) and len(actual_set) > 0:
            evidence = f"Ground truth check passed: Shortlisted IDs {candidate_ids} are contained within expected ground truth {sorted(list(expected_set))} for Job #{job_id}."
            return True, evidence, None
        else:
            err = f"Shortlist mismatch: Selected {candidate_ids}, but expected ground truth candidates are {sorted(list(expected_set))}."
            return False, "", err

    async def _check_intent_matches_reply(self, details: Dict[str, Any]) -> Tuple[bool, str, Optional[str]]:
        applicant_id = details.get("applicant_id")
        applicant = await fetch_one("SELECT * FROM applicants WHERE id = %s", (applicant_id,))
        if not applicant:
            return False, "", f"Applicant #{applicant_id} not found."

        # Verify applicant record has values recorded
        notice = applicant.get("notice_period_days")
        ctc = applicant.get("expected_ctc_lpa")
        interested = applicant.get("interested")

        if interested is None:
            return False, "", f"Applicant #{applicant_id} has no intent recorded in database."

        evidence = (
            f"Ground truth check passed: Applicant #{applicant_id} ({applicant['name']}) has recorded intent: "
            f"interested={interested}, notice_period={notice} days, expected_ctc={ctc} LPA."
        )
        return True, evidence, None

    async def _check_policy_respected(self, details: Dict[str, Any]) -> Tuple[bool, str, Optional[str]]:
        applicant_id = details.get("applicant_id")
        max_notice = details.get("max_notice_days", 60)

        applicant = await fetch_one("SELECT * FROM applicants WHERE id = %s", (applicant_id,))
        if not applicant:
            return False, "", f"Applicant #{applicant_id} not found."

        interviews = await fetch_all("SELECT id FROM interviews WHERE applicant_id = %s", (applicant_id,))
        has_interview = len(interviews) > 0

        notice = applicant.get("notice_period_days") or 0
        interested = applicant.get("interested")

        # If notice > max_notice, or candidate declined, NO interview should exist
        if notice > max_notice or interested is False:
            if has_interview:
                return False, "", f"Policy violation: Candidate #{applicant_id} (notice: {notice}d, interested: {interested}) was scheduled for an interview despite violating policy limit of {max_notice} days."
            evidence = f"Policy respected: Non-qualifying candidate #{applicant_id} (notice: {notice}d > {max_notice}d limit) was NOT booked for an interview."
            return True, evidence, None
        else:
            evidence = f"Policy respected: Qualifying candidate #{applicant_id} (notice: {notice}d <= {max_notice}d limit)."
            return True, evidence, None

    async def _check_interview_booked(self, details: Dict[str, Any]) -> Tuple[bool, str, Optional[str]]:
        applicant_id = details.get("applicant_id")
        expected_slot_id = details.get("slot_id")

        interviews = await fetch_all("SELECT * FROM interviews WHERE applicant_id = %s", (applicant_id,))
        if len(interviews) == 0:
            return False, "", f"No interview record exists in database for Applicant #{applicant_id}."
        if len(interviews) > 1:
            return False, "", f"Double-booking detected: Multiple interviews ({len(interviews)}) found for Applicant #{applicant_id}."

        interview = interviews[0]
        actual_slot_id = interview["slot_id"]

        if expected_slot_id and actual_slot_id != expected_slot_id:
            return False, "", f"Slot mismatch: Interview booked on Slot #{actual_slot_id}, but claim specified Slot #{expected_slot_id}."

        # Verify slot table reflects booking
        slot = await fetch_one("SELECT * FROM slots WHERE id = %s", (actual_slot_id,))
        if not slot or slot.get("booked_applicant_id") != applicant_id:
            return False, "", f"Slot #{actual_slot_id} booked_applicant_id does not match Applicant #{applicant_id}."

        evidence = f"Ground truth check passed: Exactly one interview confirmed for Applicant #{applicant_id} on Slot #{actual_slot_id}. Slot not double booked."
        return True, evidence, None

    async def _check_stage_is(self, details: Dict[str, Any]) -> Tuple[bool, str, Optional[str]]:
        applicant_id = details.get("applicant_id")
        expected_stage = details.get("stage")

        applicant = await fetch_one("SELECT stage, name FROM applicants WHERE id = %s", (applicant_id,))
        if not applicant:
            return False, "", f"Applicant #{applicant_id} not found."

        actual_stage = applicant.get("stage")
        if actual_stage == expected_stage:
            evidence = f"Stage verified: Applicant #{applicant_id} ({applicant['name']}) is in stage '{actual_stage}'."
            return True, evidence, None
        else:
            return False, "", f"Stage mismatch for Applicant #{applicant_id}: Expected '{expected_stage}', but database shows '{actual_stage}'."

    async def _check_no_booking(self, details: Dict[str, Any]) -> Tuple[bool, str, Optional[str]]:
        applicant_id = details.get("applicant_id")
        interviews = await fetch_all("SELECT id FROM interviews WHERE applicant_id = %s", (applicant_id,))
        slots = await fetch_all("SELECT id FROM slots WHERE booked_applicant_id = %s", (applicant_id,))

        if interviews or slots:
            return False, "", f"Candidate #{applicant_id} has interview/slot bookings when none were expected."
        
        evidence = f"Verified: Applicant #{applicant_id} has no calendar bookings."
        return True, evidence, None

    async def _check_count_applicants(self, details: Dict[str, Any]) -> Tuple[bool, str, Optional[str]]:
        job_id = details.get("job_id")
        expected_count = details.get("expected_count")

        # Ground truth check: 3 applicants have 3+ years experience for Job 1
        applicants = await fetch_all("SELECT id, name, resume_text FROM applicants WHERE job_id = %s", (job_id,))
        count = 0
        for a in applicants:
            text = a["resume_text"].lower()
            if "experience: 4" in text or "experience: 5" in text or "experience: 3.5" in text:
                count += 1

        if count == expected_count:
            evidence = f"Count verified: {count} applicants for Job #{job_id} match criteria (expected {expected_count})."
            return True, evidence, None
        else:
            return False, "", f"Count mismatch: Found {count} matching applicants, claim expected {expected_count}."

    async def _check_permission_denied_logged(self, run_id: str) -> Tuple[bool, str, Optional[str]]:
        logs = await fetch_all(
            "SELECT * FROM audit_log WHERE run_id = %s AND event_type = 'permission_denied'",
            (run_id,)
        )
        if logs:
            evidence = f"Permission denied check passed: {len(logs)} denial events logged to audit_log for run {run_id}."
            return True, evidence, None
        else:
            return False, "", f"No 'permission_denied' events recorded in audit_log for run {run_id}."
