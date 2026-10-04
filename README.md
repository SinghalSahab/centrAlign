# CentrAlign AI Workforce Layer — Prototype Runtime

Working prototype for the **CentrAlign AI Engineering Internship take-home**.

CentrAlign builds an autonomous AI workforce layer where specialized AI employees (recruiter, analyst, ops, SDR) operate on a shared platform with reasoning, company memory, knowledge retrieval, permission enforcement, and human escalation.

This prototype implements that generic agent runtime with two configured roles:
- **Recruiter** (main): Sources candidates, scores resumes against rubrics, verifies intent on Telegram, and schedules interviews in ATS & Calendar.
- **Analyst** (generalization): Executes quantitative candidate queries in read-only mode, proving that write tools are blocked by the permission layer without modifying core code.

---

## Key Highlights & Verification

- **Real internal apps, not mocks**: Two server-rendered web applications hosted in FastAPI (`/sandbox/ats` and `/sandbox/calendar`) with session cookies, stage order validation, numeric CTC checks, and conflict avoidance.
- **Independent Ground-Truth Verifier (`verifier.py`)**: Evaluates agent claims directly against Postgres database state after every run.
- **100% Pass Rate on 8 Programmatic Benchmark Evals**:
  - Happy Path (Screen, Shortlist, Verify Intent, Schedule)
  - Candidate Declines Offer (Stage updated to Rejected without booking)
  - Notice Period > 60d Policy Violation (Policy enforced, no interview)
  - Slot Taken Race Condition (Adapts to next free slot)
  - Expired Session Re-authentication Recovery (401 auto re-login)
  - CTC Input Format Self-Correction (Converts '18 lakhs' to numeric 18)
  - Ambiguous Requisition Clarification (`ask_user`)
  - Analyst Read-Only & Permission Denial Check
- **Zero Agent Frameworks**: Handcrafted ~200 line observe-reason-act loop with loop detection, memory scratchpad, and compact DOM snapshots.

---

## Project Structure

```text
/backend
  app/main.py              # FastAPI app, CORS, routers, lifespan
  app/agent/loop.py        # Generic agent loop (~200 lines)
  app/agent/llm.py         # Gemini API wrapper with native function calling
  app/agent/tools.py       # Tool schemas & implementations
  app/agent/browser.py     # HTTP browser: cookie sessions, compact DOM snapshot
  app/agent/memory.py      # Company memory scratchpad + rolling summary
  app/agent/permissions.py # Permission layer (role -> allowed tools/apps)
  app/agent/errors.py      # Error classifier and self-healing strategies
  app/agent/verifier.py    # Independent ground-truth verifier
  app/agent/prompts.py     # Base system prompt + dynamic role playbook builder
  app/roles/               # recruiter.yaml, analyst.yaml
  app/knowledge/           # Seed policy docs & full-text search
  app/messaging/           # base.py, telegram.py, fake.py
  app/sandbox/ats/         # ATS server-rendered web application
  app/sandbox/calendar/    # Calendar server-rendered web application
  app/sandbox/faults.py    # Fault injection middleware
  app/api/                 # runs.py, evals.py, telegram.py
  evals/                   # tasks.py (8 benchmark scenarios), runner.py
  migrations/              # Postgres & SQLite schema migrations
  tests/                   # Pytest unit tests (permissions, errors, verifier, loop)
  seed.py                  # Seed script (jobs, resumes, interviewers, slots, policies)
/frontend                  # Next.js App Router (Console, Live Inspector, Evals, Sandbox)
/docs                      # ARCHITECTURE.md, USER_GUIDE.md
```

---

## Quick Start

### 1. Backend
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r backend/requirements.txt
export PYTHONPATH=backend
python3 backend/seed.py
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

### 2. Frontend
```bash
cd frontend
npm install
npm run dev
```
Open [http://localhost:3000](http://localhost:3000) to access the console.

### 3. Run Benchmark Suite (8 Scenarios)
```bash
source .venv/bin/activate
export PYTHONPATH=backend
python3 backend/evals/runner.py
```

For full architecture details, see [ARCHITECTURE.md](file:///Users/prakhar/certiAlign/docs/ARCHITECTURE.md).
For deployment on Render & Vercel, see [USER_GUIDE.md](file:///Users/prakhar/certiAlign/docs/USER_GUIDE.md).
