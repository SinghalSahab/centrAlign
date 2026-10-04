from typing import Any, Dict, List

EVAL_TASKS: List[Dict[str, Any]] = [
    {
        "id": "eval_01_happy_path",
        "name": "Happy Path: Screen, Shortlist, Intent, Schedule",
        "role": "recruiter",
        "task": (
            "We're hiring a Senior Backend Engineer. Review the applicants against our hiring rubric, "
            "shortlist the best candidate, confirm their interest, notice period and expected CTC on Telegram, "
            "and book an interview with the hiring manager. Update the ATS and report when done."
        ),
        "faults": [],
        "auto_approve": True,
        "scripted_replies": {
            1: "Yes, very interested! Notice period is 30 days and expected CTC is 22 LPA."
        },
        "expected_claims": ["shortlist_valid", "intent_matches_reply", "policy_respected", "interview_booked", "stage_is"]
    },
    {
        "id": "eval_02_candidate_declines",
        "name": "Candidate Declines Offer",
        "role": "recruiter",
        "task": (
            "Review applicants for Senior Backend Engineer, reach out to Pooja Sundaram (#5) to verify intent. "
            "If she declines, record her response and ensure no interview is scheduled."
        ),
        "faults": [],
        "auto_approve": True,
        "scripted_replies": {
            5: "Thank you for reaching out, but I have already accepted another offer and am declining this opportunity."
        },
        "expected_claims": ["policy_respected", "no_booking"]
    },
    {
        "id": "eval_03_notice_period_over_policy",
        "name": "Notice Period Over 60-Day Policy Limit",
        "role": "recruiter",
        "task": (
            "Review Rohan Verma (#3) for Senior Backend Engineer. Check company talent policy for notice period rules, "
            "verify his notice period, and adhere strictly to company policy regarding scheduling."
        ),
        "faults": [],
        "auto_approve": True,
        "scripted_replies": {
            3: "Hello, I am interested, but my company notice period is 90 days. Expected CTC is 25 LPA."
        },
        "expected_claims": ["policy_respected", "no_booking"]
    },
    {
        "id": "eval_04_slot_taken_fallback",
        "name": "Slot Conflict Race Condition Recovery",
        "role": "recruiter",
        "task": (
            "Schedule an interview for Aarav Sharma (#1). If the chosen slot is taken by another recruiter, "
            "adapt and book the next available free slot."
        ),
        "faults": ["slot_taken"],
        "auto_approve": True,
        "scripted_replies": {
            1: "Yes, interested! Notice period 30 days, CTC 22 LPA."
        },
        "expected_claims": ["interview_booked"]
    },
    {
        "id": "eval_05_expired_session",
        "name": "Expired Session Re-authentication Recovery",
        "role": "recruiter",
        "task": (
            "Open ATS, inspect applicants for Senior Backend Engineer, and update applicant #1 stage to Shortlisted."
        ),
        "faults": ["expired_session"],
        "auto_approve": True,
        "expected_claims": ["stage_is"]
    },
    {
        "id": "eval_06_intent_validation_rule",
        "name": "CTC Input Format Self-Correction",
        "role": "recruiter",
        "task": (
            "Record intent for Aarav Sharma (#1). If the system rejects non-numeric CTC (e.g. '22 lakhs'), "
            "read the validation error and resubmit with pure numeric LPA."
        ),
        "faults": ["intent_validation_rule"],
        "auto_approve": True,
        "expected_claims": ["intent_matches_reply"]
    },
    {
        "id": "eval_07_ambiguous_job",
        "name": "Ambiguous Requisition Clarification (ask_user)",
        "role": "recruiter",
        "task": (
            "We're hiring for the engineering role. Review applicants and proceed."
        ),
        "faults": [],
        "auto_approve": True,
        "expected_tool": "ask_user"
    },
    {
        "id": "eval_08_analyst_permission_denial",
        "name": "Analyst Role: Read-only Queries & Permission Denial",
        "role": "analyst",
        "task": (
            "How many Backend Engineer applicants have 3+ years of Python? "
            "Also attempt write operation to verify system permission layer."
        ),
        "faults": [],
        "auto_approve": True,
        "expected_claims": ["count_applicants", "permission_denied_logged"]
    }

]
