-- Platform and Sandbox Schema for CentrAlign Prototype

-- Sandbox Tables
CREATE TABLE IF NOT EXISTS jobs (
    id SERIAL PRIMARY KEY,
    title TEXT NOT NULL,
    jd_text TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'active',
    expected_shortlist_ids INT[] DEFAULT '{}'
);

CREATE TABLE IF NOT EXISTS applicants (
    id SERIAL PRIMARY KEY,
    job_id INT REFERENCES jobs(id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    email TEXT NOT NULL,
    phone TEXT NOT NULL,
    resume_text TEXT NOT NULL,
    stage TEXT NOT NULL DEFAULT 'Applied',
    interested BOOLEAN DEFAULT NULL,
    notice_period_days INT DEFAULT NULL,
    expected_ctc_lpa NUMERIC DEFAULT NULL,
    intent_notes TEXT DEFAULT NULL
);

CREATE TABLE IF NOT EXISTS interviewers (
    id SERIAL PRIMARY KEY,
    name TEXT NOT NULL,
    email TEXT NOT NULL,
    role TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS slots (
    id SERIAL PRIMARY KEY,
    interviewer_id INT REFERENCES interviewers(id) ON DELETE CASCADE,
    start_ts TIMESTAMPTZ NOT NULL,
    booked_applicant_id INT REFERENCES applicants(id) ON DELETE SET NULL
);

CREATE TABLE IF NOT EXISTS interviews (
    id SERIAL PRIMARY KEY,
    applicant_id INT REFERENCES applicants(id) ON DELETE CASCADE,
    slot_id INT UNIQUE REFERENCES slots(id) ON DELETE CASCADE,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS knowledge_docs (
    id SERIAL PRIMARY KEY,
    title TEXT NOT NULL,
    body TEXT NOT NULL,
    tsv TSVECTOR GENERATED ALWAYS AS (to_tsvector('english', title || ' ' || body)) STORED
);
CREATE INDEX IF NOT EXISTS idx_knowledge_docs_tsv ON knowledge_docs USING GIN(tsv);

-- Platform Tables
CREATE TABLE IF NOT EXISTS runs (
    id UUID PRIMARY KEY,
    role TEXT NOT NULL,
    task TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'running',
    faults JSONB DEFAULT '[]'::jsonb,
    auto_approve BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMPTZ,
    summary TEXT,
    claims JSONB,
    error TEXT
);

CREATE TABLE IF NOT EXISTS steps (
    id SERIAL PRIMARY KEY,
    run_id UUID REFERENCES runs(id) ON DELETE CASCADE,
    step_number INT NOT NULL,
    action_type TEXT NOT NULL,
    tool_name TEXT,
    tool_args JSONB,
    tool_result JSONB,
    observation TEXT,
    error TEXT,
    recovery_action TEXT,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_steps_run_id ON steps(run_id);

CREATE TABLE IF NOT EXISTS memory_facts (
    id SERIAL PRIMARY KEY,
    run_id UUID REFERENCES runs(id) ON DELETE CASCADE,
    key TEXT NOT NULL,
    value JSONB NOT NULL,
    source TEXT,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_memory_facts_run_id ON memory_facts(run_id);

CREATE TABLE IF NOT EXISTS approvals (
    id SERIAL PRIMARY KEY,
    run_id UUID REFERENCES runs(id) ON DELETE CASCADE,
    tool_name TEXT NOT NULL,
    tool_args JSONB NOT NULL,
    reason TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'pending', -- pending, approved, rejected
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    decided_at TIMESTAMPTZ
);
CREATE INDEX IF NOT EXISTS idx_approvals_run_id ON approvals(run_id);

CREATE TABLE IF NOT EXISTS audit_log (
    id SERIAL PRIMARY KEY,
    run_id UUID REFERENCES runs(id) ON DELETE CASCADE,
    event_type TEXT NOT NULL,
    details JSONB NOT NULL,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_audit_log_run_id ON audit_log(run_id);

CREATE TABLE IF NOT EXISTS messages (
    id SERIAL PRIMARY KEY,
    run_id UUID REFERENCES runs(id) ON DELETE SET NULL,
    applicant_id INT REFERENCES applicants(id) ON DELETE CASCADE,
    direction TEXT NOT NULL, -- outbound, inbound
    text TEXT NOT NULL,
    external_id TEXT,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_messages_run_id ON messages(run_id);
CREATE INDEX IF NOT EXISTS idx_messages_applicant_id ON messages(applicant_id);

CREATE TABLE IF NOT EXISTS pending_waits (
    id SERIAL PRIMARY KEY,
    run_id UUID REFERENCES runs(id) ON DELETE CASCADE,
    applicant_id INT REFERENCES applicants(id) ON DELETE CASCADE,
    wait_type TEXT NOT NULL, -- candidate_reply, user_input
    timeout_ts TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_pending_waits_run_id ON pending_waits(run_id);

CREATE TABLE IF NOT EXISTS eval_results (
    id SERIAL PRIMARY KEY,
    task_id TEXT NOT NULL,
    run_id UUID REFERENCES runs(id) ON DELETE SET NULL,
    passed BOOLEAN NOT NULL,
    steps_count INT NOT NULL,
    retries_count INT NOT NULL,
    verified BOOLEAN NOT NULL,
    details JSONB NOT NULL,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);
