# CentrAlign Prototype User & Deployment Guide

This guide covers setup, local execution, live Telegram messaging, running evaluations, and deploying to Render & Vercel.

---

## 1. Local Quick Start

### Prerequisites
- Python 3.11+
- Node.js 18+ & npm

### Backend Setup
1. Open a terminal in the root directory:
   ```bash
   # Activate virtualenv
   source .venv/bin/activate
   export PYTHONPATH=backend

   # Copy environment example
   cp backend/.env.example backend/.env
   ```
2. Start the FastAPI backend:
   ```bash
   uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
   ```
3. The server starts with automatic database migrations and seeds initial jobs, resumes, interviewers, and policy docs.
   - **Health check**: `http://localhost:8000/health`
   - **ATS Sandbox**: `http://localhost:8000/sandbox/ats/` (user: `recruiter_admin`, pass: `ats_secret_2026`)
   - **Calendar Sandbox**: `http://localhost:8000/sandbox/calendar/` (user: `calendar_admin`, pass: `cal_secret_2026`)

### Frontend Setup
1. In a second terminal:
   ```bash
   cd frontend
   npm run dev
   ```
2. Open your browser to `http://localhost:3000`.

---

## 2. Canonical Task Walkthrough

The canonical task demonstrates the complete autonomous lifecycle:

> *"We're hiring a Senior Backend Engineer. Review the applicants against our hiring rubric, shortlist the best candidate, confirm their interest, notice period and expected CTC on Telegram, and book an interview with the hiring manager. Update the ATS and report when done."*

### Execution Flow:
1. **Understand**: The agent loads the `Recruiter` playbook (`app/roles/recruiter.yaml`).
2. **Retrieve Knowledge**: Searches `knowledge_docs` for the *Engineering Hiring Rubric* (skills 40%, experience 30%, code quality 20%).
3. **Browse ATS**: Fetches credentials from vault, logs into `/sandbox/ats/login`, opens the requisition, reads candidate resumes.
4. **Reason & Score**: Scores Aarav Sharma (92/100, 4.2 yrs at Razorpay with FastAPI/Postgres) and updates his stage to `Shortlisted`.
5. **Verify Intent**: Dispatches a Telegram message to verify interest, notice period, and CTC.
6. **Apply Policy**: Checks the *Talent Policy* doc (max 60 days notice period). Aarav confirms 30 days and 22 LPA, qualifying for an interview.
7. **Schedule**: Logs into `/sandbox/calendar/`, identifies free 45-minute slots with Lead Architect Siddharth Roy, and books Slot #1.
8. **Update ATS**: Moves candidate stage to `Interview Scheduled`.
9. **Verify**: Calls `finish` with typed claims. The independent verifier validates all database records directly in Postgres and issues a green `VERIFIED` badge.

---

## 3. Telegram Candidate Integration

In demo mode, you can play the candidate directly on your phone:

1. Obtain a free Telegram Bot Token from `@BotFather`.
2. Get your personal Chat ID from `@userinfobot`.
3. Set the environment variables in `backend/.env`:
   ```bash
   TELEGRAM_BOT_TOKEN="your_bot_token"
   TELEGRAM_CANDIDATE_CHAT_ID="your_telegram_chat_id"
   TELEGRAM_RECRUITER_CHAT_ID="your_telegram_chat_id"
   TELEGRAM_WEBHOOK_SECRET="secret_token"
   ```
4. When the agent reaches the `message_candidate` stage, a message arrives on your phone prefixed with the candidate's name.
5. Reply via Telegram (e.g., *"Yes, interested! Notice period is 30 days and expected CTC is 22 LPA"*). The webhook resumes the agent execution automatically.

---

## 4. Running the Benchmark Evals Suite (8 Scenarios)

The benchmark suite programmatically verifies the 8 core grading scenarios using `FakeMessenger` and direct database verification:

### Via Command Line:
```bash
source .venv/bin/activate
export PYTHONPATH=backend
python3 backend/evals/runner.py
```

### Via Web UI:
1. Navigate to `http://localhost:3000/evals`.
2. Click **Run Full Evaluation Suite**.
3. View real-time pass/fail rates, execution step metrics, and verifier evidence breakdowns.

### 8 Benchmark Scenarios Covered:
1. `eval_01_happy_path`: End-to-end screen, shortlist, intent verification, and scheduling.
2. `eval_02_candidate_declines`: Candidate declines offer; agent updates ATS to Rejected without booking.
3. `eval_03_notice_period_over_policy`: Candidate has 90-day notice (exceeding 60d limit); agent enforces policy and halts scheduling.
4. `eval_04_slot_taken_fallback`: First chosen slot is taken mid-run; agent adapts and books the next available free slot.
5. `eval_05_expired_session`: 401 session expiration encountered; agent re-authenticates via vault and resumes work.
6. `eval_06_intent_validation_rule`: Non-numeric CTC (e.g. '18 lakhs') rejected by sandbox; agent self-corrects format to numeric `18`.
7. `eval_07_ambiguous_job`: Ambiguous task prompt triggers `ask_user` human clarification.
8. `eval_08_analyst_permission_denial`: Analyst executes read-only analytical queries; write operation is blocked by permission layer and logged to `audit_log`.

---

## 5. Deployment Guide (Free Tiers)

### Render (Backend)
1. Create a **Web Service** on [Render](https://render.com).
2. Configure settings:
   - **Root Directory**: `backend`
   - **Environment**: `Python 3`
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
   - **Health Check Path**: `/health`
3. Add Environment Variables:
   - `DATABASE_URL`: Your pooled Neon Postgres connection string
   - `GEMINI_API_KEY`: Your Google Gemini API key
   - `GEMINI_MODEL`: `gemini-2.5-flash`
   - `ALLOWED_ORIGINS`: `https://your-frontend.vercel.app`
   - `SANDBOX_BASE_URL`: `https://your-backend.onrender.com`
   - `ADMIN_TOKEN`: Secure secret token to protect run creation
   - `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CANDIDATE_CHAT_ID`, `TELEGRAM_WEBHOOK_SECRET`

### Vercel (Frontend)
1. Import repository to [Vercel](https://vercel.com).
2. Set **Root Directory** to `frontend`.
3. Set Environment Variable:
   - `NEXT_PUBLIC_API_URL`: `https://your-backend.onrender.com`
4. Deploy!

### Free-Tier Operational Notes:
> [!NOTE]
> **Render Free Tier**: The web service sleeps after 15 minutes of inactivity. The first request after sleep may take ~30-50 seconds to wake up.

> [!NOTE]
> **Neon Free Tier**: Scales compute to zero after 5 minutes of idle time. The initial connection pool handshake automatically restarts the compute endpoint in ~1-2 seconds.
