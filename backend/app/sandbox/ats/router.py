import re
from typing import Optional
from fastapi import APIRouter, Request, Response, Form, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse

from app.db import fetch_one, fetch_all, execute
from app.sandbox.faults import apply_request_faults, get_active_faults_for_request

router = APIRouter(prefix="/sandbox/ats", tags=["ATS Sandbox"])

VALID_STAGES = ["Applied", "Shortlisted", "Intent Confirmed", "Interview Scheduled", "Rejected"]
ATS_COOKIE = "ats_session"
VALID_USERNAME = "recruiter_admin"
VALID_PASSWORD = "ats_secret_2026"

def is_authenticated(request: Request) -> bool:
    return request.cookies.get(ATS_COOKIE) == "auth_token_ats_2026"

def render_page(title: str, body: str, error: Optional[str] = None, success: Optional[str] = None) -> HTMLResponse:
    error_html = f'<div style="background:#fee2e2;color:#991b1b;padding:12px;border-radius:6px;margin-bottom:16px;" class="flash-error" id="flash-error"><strong>Error:</strong> {error}</div>' if error else ''
    success_html = f'<div style="background:#dcfce7;color:#166534;padding:12px;border-radius:6px;margin-bottom:16px;" class="flash-success" id="flash-success">{success}</div>' if success else ''
    html = f"""<!DOCTYPE html>
<html>
<head>
    <title>{title} - CentrAlign ATS</title>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
        body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; background: #f8fafc; color: #0f172a; margin: 0; padding: 24px; }}
        .container {{ max-width: 900px; margin: 0 auto; background: #ffffff; border-radius: 8px; border: 1px solid #e2e8f0; padding: 32px; box-shadow: 0 1px 3px rgba(0,0,0,0.1); }}
        h1, h2, h3 {{ color: #0f172a; margin-top: 0; }}
        a {{ color: #2563eb; text-decoration: none; font-weight: 500; }}
        a:hover {{ text-decoration: underline; }}
        table {{ width: 100%; border-collapse: collapse; margin-top: 16px; margin-bottom: 24px; }}
        th, td {{ text-align: left; padding: 12px; border-bottom: 1px solid #e2e8f0; }}
        th {{ background: #f1f5f9; font-weight: 600; }}
        .badge {{ display: inline-block; padding: 4px 8px; border-radius: 4px; font-size: 12px; font-weight: 600; }}
        .badge-Applied {{ background: #e2e8f0; color: #475569; }}
        .badge-Shortlisted {{ background: #dbeafe; color: #1e40af; }}
        .badge-IntentConfirmed {{ background: #fef3c7; color: #92400e; }}
        .badge-InterviewScheduled {{ background: #dcfce7; color: #166534; }}
        .badge-Rejected {{ background: #fee2e2; color: #991b1b; }}
        .form-group {{ margin-bottom: 16px; }}
        label {{ display: block; font-weight: 600; margin-bottom: 6px; font-size: 14px; }}
        input, select, textarea {{ width: 100%; max-width: 450px; padding: 8px 12px; border: 1px solid #cbd5e1; border-radius: 6px; font-size: 14px; }}
        button {{ background: #2563eb; color: #ffffff; border: none; padding: 10px 18px; border-radius: 6px; font-weight: 600; cursor: pointer; }}
        button:hover {{ background: #1d4ed8; }}
        .nav {{ margin-bottom: 24px; padding-bottom: 12px; border-bottom: 1px solid #e2e8f0; display: flex; justify-content: space-between; }}
        pre {{ background: #f1f5f9; padding: 12px; border-radius: 6px; font-size: 13px; white-space: pre-wrap; }}
    </style>
</head>
<body>
<div class="container">
    <div class="nav">
        <strong>CentrAlign ATS Sandbox</strong>
        <div>
            <a href="/sandbox/ats/">Jobs</a> |
            <a href="/sandbox/calendar/">Calendar</a> |
            <a href="/sandbox/ats/logout">Logout</a>
        </div>
    </div>
    {error_html}
    {success_html}
    {body}
</div>
</body>
</html>
"""
    return HTMLResponse(content=html)

@router.get("/login")
async def get_login(request: Request, error: Optional[str] = None):
    body = f"""
    <h2>Recruiter Portal Login</h2>
    <p>Please enter your credentials to access the Applicant Tracking System.</p>
    <form action="/sandbox/ats/login" method="POST" id="form-login">
        <div class="form-group">
            <label for="username">Username</label>
            <input type="text" id="username" name="username" value="recruiter_admin" required />
        </div>
        <div class="form-group">
            <label for="password">Password</label>
            <input type="password" id="password" name="password" required />
        </div>
        <button type="submit" id="btn-login">Sign In</button>
    </form>
    """
    return render_page("Sign In", body, error=error)

@router.post("/login")
async def post_login(request: Request, username: str = Form(...), password: str = Form(...)):
    await apply_request_faults(request, "ats_login")
    if username == VALID_USERNAME and password == VALID_PASSWORD:
        response = RedirectResponse(url="/sandbox/ats/", status_code=303)
        response.set_cookie(key=ATS_COOKIE, value="auth_token_ats_2026", path="/sandbox/ats", httponly=True)
        return response
    return render_page("Sign In", '<p>Invalid credentials. Try again.</p>', error="Invalid username or password.")

@router.get("/logout")
async def logout():
    response = RedirectResponse(url="/sandbox/ats/login", status_code=303)
    response.delete_cookie(key=ATS_COOKIE, path="/sandbox/ats")
    return response

@router.get("/")
async def get_jobs(request: Request):
    await apply_request_faults(request, "ats_jobs")
    if not is_authenticated(request):
        return RedirectResponse(url="/sandbox/ats/login", status_code=303)

    jobs = await fetch_all("SELECT id, title, status FROM jobs ORDER BY id ASC")
    rows = ""
    for j in jobs:
        rows += f"""
        <tr>
            <td><strong>#{j['id']}</strong></td>
            <td><a href="/sandbox/ats/jobs/{j['id']}" id="link-job-{j['id']}">{j['title']}</a></td>
            <td><span class="badge badge-Applied">{j['status'].upper()}</span></td>
            <td><a href="/sandbox/ats/jobs/{j['id']}">View Requisition &rarr;</a></td>
        </tr>
        """
    body = f"""
    <h2>Active Job Requisitions</h2>
    <table>
        <thead>
            <tr>
                <th>ID</th>
                <th>Role Title</th>
                <th>Status</th>
                <th>Action</th>
            </tr>
        </thead>
        <tbody>
            {rows}
        </tbody>
    </table>
    """
    return render_page("Job Requisitions", body)

@router.get("/jobs/{job_id}")
async def get_job_detail(request: Request, job_id: int):
    await apply_request_faults(request, f"ats_job_{job_id}")
    if not is_authenticated(request):
        return RedirectResponse(url="/sandbox/ats/login", status_code=303)

    job = await fetch_one("SELECT id, title, jd_text, status FROM jobs WHERE id = %s", (job_id,))
    if not job:
        raise HTTPException(status_code=404, detail="Job requisition not found")

    applicants = await fetch_all(
        "SELECT id, name, email, stage, expected_ctc_lpa, notice_period_days FROM applicants WHERE job_id = %s ORDER BY id ASC",
        (job_id,)
    )
    rows = ""
    for a in applicants:
        stage_cls = a['stage'].replace(" ", "")
        rows += f"""
        <tr>
            <td><strong>#{a['id']}</strong></td>
            <td><a href="/sandbox/ats/applicants/{a['id']}" id="link-applicant-{a['id']}">{a['name']}</a></td>
            <td>{a['email']}</td>
            <td><span class="badge badge-{stage_cls}">{a['stage']}</span></td>
            <td><a href="/sandbox/ats/applicants/{a['id']}">Review &rarr;</a></td>
        </tr>
        """
    body = f"""
    <div style="margin-bottom: 24px;">
        <a href="/sandbox/ats/">&larr; Back to all Requisitions</a>
    </div>
    <h2>{job['title']} (Req #{job['id']})</h2>
    <h3>Job Description</h3>
    <pre>{job['jd_text']}</pre>

    <h3>Applicants ({len(applicants)})</h3>
    <table>
        <thead>
            <tr>
                <th>ID</th>
                <th>Candidate Name</th>
                <th>Email</th>
                <th>Stage</th>
                <th>Review</th>
            </tr>
        </thead>
        <tbody>
            {rows}
        </tbody>
    </table>
    """
    return render_page(f"{job['title']}", body)

@router.get("/applicants/{applicant_id}")
async def get_applicant_detail(request: Request, applicant_id: int, error: Optional[str] = None, success: Optional[str] = None):
    await apply_request_faults(request, f"ats_applicant_{applicant_id}")
    if not is_authenticated(request):
        return RedirectResponse(url="/sandbox/ats/login", status_code=303)

    applicant = await fetch_one("SELECT * FROM applicants WHERE id = %s", (applicant_id,))
    if not applicant:
        raise HTTPException(status_code=404, detail="Applicant not found")

    job = await fetch_one("SELECT id, title FROM jobs WHERE id = %s", (applicant["job_id"],))

    faults = await get_active_faults_for_request(request)
    ctc_field_name = "ctc_lpa_expected" if "renamed_field" in faults else "expected_ctc_lpa"

    stage_options = "".join(
        f'<option value="{s}" {"selected" if s == applicant["stage"] else ""}>{s}</option>'
        for s in VALID_STAGES
    )

    stage_cls = applicant['stage'].replace(" ", "")
    body = f"""
    <div style="margin-bottom: 24px;">
        <a href="/sandbox/ats/jobs/{applicant['job_id']}">&larr; Back to {job['title'] if job else 'Requisition'}</a>
    </div>
    <h2>{applicant['name']} <span class="badge badge-{stage_cls}">{applicant['stage']}</span></h2>
    <p><strong>Email:</strong> {applicant['email']} | <strong>Phone:</strong> {applicant['phone']}</p>
    
    <h3>Resume Content</h3>
    <pre>{applicant['resume_text']}</pre>

    <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 24px; margin-top: 24px;">
        <div style="background: #f8fafc; padding: 20px; border-radius: 8px; border: 1px solid #e2e8f0;">
            <h3>Update Stage</h3>
            <form action="/sandbox/ats/applicants/{applicant_id}/stage" method="POST" id="form-update-stage">
                <div class="form-group">
                    <label for="new_stage">Current Stage: <strong>{applicant['stage']}</strong></label>
                    <select id="new_stage" name="new_stage">
                        {stage_options}
                    </select>
                </div>
                <button type="submit" id="btn-update-stage">Submit Stage Change</button>
            </form>
        </div>

        <div style="background: #f8fafc; padding: 20px; border-radius: 8px; border: 1px solid #e2e8f0;">
            <h3>Record Candidate Intent</h3>
            <form action="/sandbox/ats/applicants/{applicant_id}/intent" method="POST" id="form-record-intent">
                <div class="form-group">
                    <label for="interested">Interested in Role?</label>
                    <select id="interested" name="interested">
                        <option value="true" {"selected" if applicant['interested'] is True else ""}>Yes (Interested)</option>
                        <option value="false" {"selected" if applicant['interested'] is False else ""}>No (Declined)</option>
                    </select>
                </div>
                <div class="form-group">
                    <label for="notice_period_days">Notice Period (in Days)</label>
                    <input type="number" id="notice_period_days" name="notice_period_days" value="{applicant['notice_period_days'] or ''}" placeholder="e.g. 30" />
                </div>
                <div class="form-group">
                    <label for="{ctc_field_name}">Expected CTC (in LPA numeric)</label>
                    <input type="text" id="{ctc_field_name}" name="{ctc_field_name}" value="{applicant['expected_ctc_lpa'] or ''}" placeholder="e.g. 22" />
                </div>
                <div class="form-group">
                    <label for="intent_notes">Verification Notes</label>
                    <textarea id="intent_notes" name="intent_notes" rows="3">{applicant['intent_notes'] or ''}</textarea>
                </div>
                <button type="submit" id="btn-save-intent">Save Intent Details</button>
            </form>
        </div>
    </div>
    """
    return render_page(f"Candidate - {applicant['name']}", body, error=error, success=success)

@router.post("/applicants/{applicant_id}/stage")
async def update_applicant_stage(request: Request, applicant_id: int, new_stage: str = Form(...)):
    await apply_request_faults(request, f"ats_stage_{applicant_id}")
    if not is_authenticated(request):
        return RedirectResponse(url="/sandbox/ats/login", status_code=303)

    applicant = await fetch_one("SELECT * FROM applicants WHERE id = %s", (applicant_id,))
    if not applicant:
        raise HTTPException(status_code=404, detail="Applicant not found")

    current_stage = applicant["stage"]

    # Enforce stage order rules:
    # Cannot go to Interview Scheduled before Intent Confirmed!
    if new_stage == "Interview Scheduled" and current_stage != "Intent Confirmed":
        err_msg = f"Invalid stage transition: Cannot move to 'Interview Scheduled' directly from '{current_stage}'. Candidate must first be in 'Intent Confirmed' stage."
        return await get_applicant_detail(request, applicant_id, error=err_msg)

    # Cannot jump to Intent Confirmed before Shortlisted (unless currently Shortlisted or already Intent Confirmed)
    if new_stage == "Intent Confirmed" and current_stage not in ["Shortlisted", "Intent Confirmed"]:
        err_msg = f"Invalid stage transition: Cannot move to 'Intent Confirmed' from '{current_stage}'. Candidate must first be 'Shortlisted'."
        return await get_applicant_detail(request, applicant_id, error=err_msg)

    await execute("UPDATE applicants SET stage = %s WHERE id = %s", (new_stage, applicant_id))
    return await get_applicant_detail(request, applicant_id, success=f"Stage successfully updated to '{new_stage}'.")

@router.post("/applicants/{applicant_id}/intent")
async def record_applicant_intent(request: Request, applicant_id: int):
    await apply_request_faults(request, f"ats_intent_{applicant_id}")
    if not is_authenticated(request):
        return RedirectResponse(url="/sandbox/ats/login", status_code=303)

    form_data = await request.form()
    interested_val = form_data.get("interested", "true").lower() in ("true", "1", "yes")
    notice_str = form_data.get("notice_period_days")
    notes_val = form_data.get("intent_notes", "")

    # Handle potentially renamed CTC field
    ctc_raw = form_data.get("expected_ctc_lpa") or form_data.get("ctc_lpa_expected")

    # CTC Numeric Validation Rule (or intent_validation_rule fault)
    faults = await get_active_faults_for_request(request)
    ctc_val = None
    if ctc_raw is not None and str(ctc_raw).strip() != "":
        raw_str = str(ctc_raw).strip()
        # If strict validation or fault injected: must be purely numeric float/int, not "18 lakhs" or "20 LPA"
        if "intent_validation_rule" in faults or not re.match(r"^\d+(\.\d+)?$", raw_str):
            if not re.match(r"^\d+(\.\d+)?$", raw_str):
                err = f"Validation Error: Expected CTC must be a plain numeric number in LPA (e.g. 18 or 24.5). Received non-numeric format: '{raw_str}'."
                return await get_applicant_detail(request, applicant_id, error=err)
        try:
            ctc_val = float(raw_str)
        except ValueError:
            err = f"Validation Error: Could not parse '{raw_str}' as a number. Please provide a numeric value in LPA."
            return await get_applicant_detail(request, applicant_id, error=err)

    notice_val = None
    if notice_str:
        try:
            notice_val = int(notice_str)
        except ValueError:
            pass

    await execute(
        """UPDATE applicants 
           SET interested = %s, notice_period_days = %s, expected_ctc_lpa = %s, intent_notes = %s 
           WHERE id = %s""",
        (interested_val, notice_val, ctc_val, notes_val, applicant_id)
    )
    return await get_applicant_detail(request, applicant_id, success="Candidate intent details recorded successfully.")
