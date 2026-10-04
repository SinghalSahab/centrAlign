from typing import Optional
from fastapi import APIRouter, Request, Response, Form, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse

from app.db import fetch_one, fetch_all, execute
from app.sandbox.faults import apply_request_faults, get_active_faults_for_request

router = APIRouter(prefix="/sandbox/calendar", tags=["Calendar Sandbox"])

CAL_COOKIE = "cal_session"
VALID_USERNAME = "calendar_admin"
VALID_PASSWORD = "cal_secret_2026"

def is_authenticated(request: Request) -> bool:
    return request.cookies.get(CAL_COOKIE) == "auth_token_cal_2026"

def render_page(title: str, body: str, error: Optional[str] = None, success: Optional[str] = None) -> HTMLResponse:
    error_html = f'<div style="background:#fee2e2;color:#991b1b;padding:12px;border-radius:6px;margin-bottom:16px;" class="flash-error" id="flash-error"><strong>Error:</strong> {error}</div>' if error else ''
    success_html = f'<div style="background:#dcfce7;color:#166534;padding:12px;border-radius:6px;margin-bottom:16px;" class="flash-success" id="flash-success">{success}</div>' if success else ''
    html = f"""<!DOCTYPE html>
<html>
<head>
    <title>{title} - CentrAlign Calendar</title>
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
        .badge-Free {{ background: #dcfce7; color: #166534; }}
        .badge-Booked {{ background: #fee2e2; color: #991b1b; }}
        .form-group {{ margin-bottom: 16px; }}
        label {{ display: block; font-weight: 600; margin-bottom: 6px; font-size: 14px; }}
        select, input {{ width: 100%; max-width: 450px; padding: 8px 12px; border: 1px solid #cbd5e1; border-radius: 6px; font-size: 14px; }}
        button {{ background: #2563eb; color: #ffffff; border: none; padding: 10px 18px; border-radius: 6px; font-weight: 600; cursor: pointer; }}
        button:hover {{ background: #1d4ed8; }}
        .nav {{ margin-bottom: 24px; padding-bottom: 12px; border-bottom: 1px solid #e2e8f0; display: flex; justify-content: space-between; }}
    </style>
</head>
<body>
<div class="container">
    <div class="nav">
        <strong>CentrAlign Calendar Sandbox</strong>
        <div>
            <a href="/sandbox/ats/">ATS</a> |
            <a href="/sandbox/calendar/">Calendar</a> |
            <a href="/sandbox/calendar/logout">Logout</a>
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
    <h2>Interview Calendar Portal Login</h2>
    <p>Please enter your credentials to manage interview schedules.</p>
    <form action="/sandbox/calendar/login" method="POST" id="form-login">
        <div class="form-group">
            <label for="username">Username</label>
            <input type="text" id="username" name="username" value="calendar_admin" required />
        </div>
        <div class="form-group">
            <label for="password">Password</label>
            <input type="password" id="password" name="password" required />
        </div>
        <button type="submit" id="btn-login">Sign In</button>
    </form>
    """
    return render_page("Calendar Sign In", body, error=error)

@router.post("/login")
async def post_login(request: Request, username: str = Form(...), password: str = Form(...)):
    await apply_request_faults(request, "cal_login")
    if username == VALID_USERNAME and password == VALID_PASSWORD:
        response = RedirectResponse(url="/sandbox/calendar/", status_code=303)
        response.set_cookie(key=CAL_COOKIE, value="auth_token_cal_2026", path="/sandbox/calendar", httponly=True)
        return response
    return render_page("Sign In", '<p>Invalid credentials.</p>', error="Invalid username or password.")

@router.get("/logout")
async def logout():
    response = RedirectResponse(url="/sandbox/calendar/login", status_code=303)
    response.delete_cookie(key=CAL_COOKIE, path="/sandbox/calendar")
    return response

@router.get("/")
async def get_calendar(request: Request, error: Optional[str] = None, success: Optional[str] = None):
    await apply_request_faults(request, "cal_overview")
    if not is_authenticated(request):
        return RedirectResponse(url="/sandbox/calendar/login", status_code=303)

    slots = await fetch_all("""
        SELECT s.id, s.start_ts, s.booked_applicant_id, i.name as interviewer_name, i.role as interviewer_role,
               a.name as booked_candidate_name
        FROM slots s
        JOIN interviewers i ON s.interviewer_id = i.id
        LEFT JOIN applicants a ON s.booked_applicant_id = a.id
        ORDER BY s.start_ts ASC
    """)

    free_slots = [s for s in slots if s["booked_applicant_id"] is None]

    # Applicants eligible for scheduling (Intent Confirmed)
    eligible_applicants = await fetch_all(
        "SELECT id, name, stage FROM applicants WHERE stage = 'Intent Confirmed' ORDER BY id ASC"
    )

    all_applicants = await fetch_all(
        "SELECT id, name, stage FROM applicants ORDER BY id ASC"
    )

    rows = ""
    for s in slots:
        status_badge = f'<span class="badge badge-Booked">Booked ({s["booked_candidate_name"]})</span>' if s["booked_applicant_id"] else '<span class="badge badge-Free">Free</span>'
        rows += f"""
        <tr>
            <td><strong>#{s['id']}</strong></td>
            <td>{s['interviewer_name']} ({s['interviewer_role']})</td>
            <td>{s['start_ts']}</td>
            <td>{status_badge}</td>
        </tr>
        """

    slot_options = "".join(
        f'<option value="{s["id"]}">Slot #{s["id"]}: {s["interviewer_name"]} at {s["start_ts"]}</option>'
        for s in free_slots
    )

    applicant_options = "".join(
        f'<option value="{a["id"]}">{a["name"]} (Stage: {a["stage"]})</option>'
        for a in all_applicants
    )

    body = f"""
    <h2>Engineering Interview Calendar</h2>
    <p>View upcoming 45-minute slots and schedule confirmed candidates.</p>
    
    <h3>All Slots</h3>
    <table>
        <thead>
            <tr>
                <th>Slot ID</th>
                <th>Interviewer</th>
                <th>Start Time</th>
                <th>Status</th>
            </tr>
        </thead>
        <tbody>
            {rows}
        </tbody>
    </table>

    <div style="background: #f8fafc; padding: 24px; border-radius: 8px; border: 1px solid #e2e8f0; margin-top: 32px;">
        <h3>Book Interview</h3>
        <p style="font-size: 13px; color: #64748b;">Note: Candidate must be in 'Intent Confirmed' stage before scheduling.</p>
        <form action="/sandbox/calendar/book" method="POST" id="form-book-interview">
            <div class="form-group">
                <label for="slot_id">Select Free Slot</label>
                <select id="slot_id" name="slot_id" required>
                    {slot_options if slot_options else '<option disabled>No free slots available</option>'}
                </select>
            </div>
            <div class="form-group">
                <label for="applicant_id">Select Candidate</label>
                <select id="applicant_id" name="applicant_id" required>
                    {applicant_options}
                </select>
            </div>
            <button type="submit" id="btn-book-slot" {"disabled" if not slot_options else ""}>Confirm Interview Booking</button>
        </form>
    </div>
    """
    return render_page("Calendar Overview", body, error=error, success=success)

@router.post("/book")
async def book_interview(request: Request, slot_id: int = Form(...), applicant_id: int = Form(...)):
    await apply_request_faults(request, f"cal_book_{slot_id}")
    if not is_authenticated(request):
        return RedirectResponse(url="/sandbox/calendar/login", status_code=303)

    slot = await fetch_one("SELECT * FROM slots WHERE id = %s", (slot_id,))
    if not slot:
        return await get_calendar(request, error=f"Slot #{slot_id} does not exist.")

    applicant = await fetch_one("SELECT * FROM applicants WHERE id = %s", (applicant_id,))
    if not applicant:
        return await get_calendar(request, error=f"Applicant #{applicant_id} does not exist.")

    # Check for slot_taken fault injection (trips once per run on first attempt)
    faults = await get_active_faults_for_request(request)
    if "slot_taken" in faults:
        run_id = request.headers.get("X-Run-Id", "default")
        from app.sandbox.faults import _flaky_attempts
        key = f"{run_id}:slot_taken_tripped"
        if key not in _flaky_attempts:
            _flaky_attempts.add(key)
            # Simulate race condition: slot booked by someone else
            await execute("UPDATE slots SET booked_applicant_id = 999 WHERE id = %s", (slot_id,))
            return await get_calendar(request, error=f"Slot conflict: Slot #{slot_id} was just taken by another recruiter. Please select an alternate free slot.")


    # Rule: Slot must be currently free
    if slot["booked_applicant_id"] is not None:
        return await get_calendar(request, error=f"Slot conflict: Slot #{slot_id} is already booked. Please choose an alternative slot.")

    # Rule: Applicant stage must be Intent Confirmed
    if applicant["stage"] != "Intent Confirmed":
        return await get_calendar(
            request,
            error=f"Booking Error: Applicant '{applicant['name']}' is currently in stage '{applicant['stage']}'. Candidates must reach 'Intent Confirmed' stage before scheduling."
        )

    # Rule: No double-booking of applicant
    existing_interview = await fetch_one("SELECT id, slot_id FROM interviews WHERE applicant_id = %s", (applicant_id,))
    if existing_interview:
        return await get_calendar(request, error=f"Booking Error: Applicant '{applicant['name']}' already has an interview booked (Slot #{existing_interview['slot_id']}).")

    # Perform Booking
    await execute("UPDATE slots SET booked_applicant_id = %s WHERE id = %s", (applicant_id, slot_id))
    await execute("INSERT INTO interviews (applicant_id, slot_id) VALUES (%s, %s)", (applicant_id, slot_id))
    await execute("UPDATE applicants SET stage = 'Interview Scheduled' WHERE id = %s", (applicant_id,))

    return await get_calendar(request, success=f"Successfully booked Slot #{slot_id} for {applicant['name']}! Candidate stage updated to 'Interview Scheduled'.")
