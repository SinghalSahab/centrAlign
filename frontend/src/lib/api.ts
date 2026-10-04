export const API_BASE = (process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000").replace(/\/$/, "");

export interface Step {
  id?: number;
  step_number: number;
  action_type: string;
  tool_name?: string;
  tool_args?: any;
  tool_result?: any;
  observation?: string;
  error?: string;
  recovery_action?: string;
  created_at?: string;
}

export interface Run {
  id: string;
  role: string;
  task: string;
  status: string;
  faults: string[];
  auto_approve: boolean;
  summary?: string;
  claims?: any[];
  error?: string;
  created_at: string;
  completed_at?: string;
}

export interface VerificationReport {
  all_passed: boolean;
  total_checks: number;
  passed_checks: number;
  failed_checks: number;
  check_results: Array<{
    type: string;
    passed: boolean;
    evidence: string;
    error?: string;
  }>;
}

export interface RunDetailResponse {
  run: Run;
  verification?: VerificationReport;
  steps: Step[];
  memory_facts: Array<{ key: string; value: any; source?: string; created_at: string }>;
  approvals: Array<{ id: number; tool_name: string; tool_args: any; reason: string; status: string }>;
  audit_logs: Array<{ id: number; event_type: string; details: any; created_at: string }>;
  messages: Array<{ id: number; direction: string; text: string; created_at: string }>;
}

export async function fetchHealth() {
  try {
    const res = await fetch(`${API_BASE}/health`, { cache: "no-store" });
    return await res.json();
  } catch (e) {
    return { status: "unreachable", error: String(e) };
  }
}

export async function createRun(payload: {
  role: string;
  task: string;
  faults: string[];
  auto_approve: boolean;
  admin_token?: string;
}): Promise<{ run_id: string; status: string }> {
  const headers: Record<string, string> = { "Content-Type": "application/json" };
  if (payload.admin_token) {
    headers["X-Admin-Token"] = payload.admin_token;
  }

  const res = await fetch(`${API_BASE}/api/runs`, {
    method: "POST",
    headers,
    body: JSON.stringify({
      role: payload.role,
      task: payload.task,
      faults: payload.faults,
      auto_approve: payload.auto_approve,
    }),
  });

  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || "Failed to create run");
  }
  return await res.json();
}

export async function listRuns(limit: number = 15): Promise<Run[]> {
  const res = await fetch(`${API_BASE}/api/runs?limit=${limit}`, { cache: "no-store" });
  if (!res.ok) throw new Error("Failed to fetch runs");
  const data = await res.json();
  return data.runs || [];
}

export async function getRunDetail(runId: string): Promise<RunDetailResponse> {
  const res = await fetch(`${API_BASE}/api/runs/${runId}`, { cache: "no-store" });
  if (!res.ok) throw new Error("Failed to fetch run details");
  return await res.json();
}

export async function approveRunAction(runId: string, approvalId: number, decision: "approved" | "rejected") {
  const res = await fetch(`${API_BASE}/api/runs/${runId}/approve`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ approval_id: approvalId, decision }),
  });
  return await res.json();
}

export async function replyToRun(runId: string, reply: string) {
  const res = await fetch(`${API_BASE}/api/runs/${runId}/reply`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ reply }),
  });
  return await res.json();
}

export async function getEvalsSummary() {
  const res = await fetch(`${API_BASE}/api/evals`, { cache: "no-store" });
  if (!res.ok) throw new Error("Failed to fetch evals summary");
  return await res.json();
}

export async function triggerEvalsBenchmark() {
  const res = await fetch(`${API_BASE}/api/evals/run`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
  });
  if (!res.ok) throw new Error("Failed to run evals benchmark");
  return await res.json();
}
