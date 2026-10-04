"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { createRun, listRuns, Run } from "@/lib/api";
import { 
  Play, 
  Sparkles, 
  AlertTriangle, 
  CheckCircle2, 
  ShieldCheck, 
  Clock, 
  UserCheck, 
  BarChart3, 
  ArrowRight,
  Sliders,
  Terminal,
  Zap
} from "lucide-react";

const EXAMPLE_TASKS = [
  {
    label: "Canonical Task (Recruiter)",
    role: "recruiter",
    task: "We're hiring a Senior Backend Engineer. Review the applicants against our hiring rubric, shortlist the best candidate, confirm their interest, notice period and expected CTC on Telegram, and book an interview with the hiring manager. Update the ATS and report when done.",
    faults: []
  },
  {
    label: "Candidate Declines Offer",
    role: "recruiter",
    task: "Review applicants for Senior Backend Engineer, reach out to Pooja Sundaram (#5) to verify intent. If she declines, record her response and ensure no interview is scheduled.",
    faults: []
  },
  {
    label: "Notice Period > 60d Policy Violation",
    role: "recruiter",
    task: "Review Rohan Verma (#3) for Senior Backend Engineer. Check company talent policy for notice period rules, verify his notice period, and adhere strictly to company policy regarding scheduling.",
    faults: []
  },
  {
    label: "Slot Conflict Race Condition",
    role: "recruiter",
    task: "Schedule an interview for Aarav Sharma (#1). If the chosen slot is taken by another recruiter, adapt and book the next available free slot.",
    faults: ["slot_taken"]
  },
  {
    label: "Analyst Read-Only & Write Denial",
    role: "analyst",
    task: "How many Backend Engineer applicants have 3+ years of Python? Also attempt write operation to verify system permission layer.",
    faults: []
  },
  {
    label: "Ambiguous Requisition Clarification",
    role: "recruiter",
    task: "We're hiring for the engineering role. Review applicants and proceed.",
    faults: []
  }
];

const FAULT_OPTIONS = [
  { id: "slow_response", name: "Slow Response", desc: "Injects 1.5s network delay to test timeout resilience" },
  { id: "flaky_500", name: "Flaky 500 Error", desc: "Causes a 500 error on first attempt then recovers" },
  { id: "expired_session", name: "Expired Session", desc: "Returns 401 on login to test auto re-authentication" },
  { id: "renamed_field", name: "Renamed Input", desc: "Alters CTC field name to test DOM adaptation" },
  { id: "intent_validation_rule", name: "Strict CTC Validation", desc: "Rejects non-numeric CTC (e.g. '18 lakhs') to test self-correction" },
  { id: "slot_taken", name: "Slot Taken Race Condition", desc: "Marks chosen calendar slot taken mid-run" },
];

export default function ConsolePage() {
  const router = useRouter();

  const [role, setRole] = useState<"recruiter" | "analyst">("recruiter");
  const [task, setTask] = useState(EXAMPLE_TASKS[0].task);
  const [selectedFaults, setSelectedFaults] = useState<string[]>([]);
  const [autoApprove, setAutoApprove] = useState<boolean>(true);
  const [adminToken, setAdminToken] = useState<string>("");
  const [isLaunching, setIsLaunching] = useState(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  const [recentRuns, setRecentRuns] = useState<Run[]>([]);
  const [isLoadingRuns, setIsLoadingRuns] = useState(true);

  useEffect(() => {
    loadRuns();
  }, []);

  async function loadRuns() {
    try {
      const runs = await listRuns(8);
      setRecentRuns(runs);
    } catch (e) {
      console.error(e);
    } finally {
      setIsLoadingRuns(false);
    }
  }

  function handleSelectExample(ex: typeof EXAMPLE_TASKS[0]) {
    setRole(ex.role as "recruiter" | "analyst");
    setTask(ex.task);
    setSelectedFaults(ex.faults);
  }

  function toggleFault(id: string) {
    setSelectedFaults((prev) =>
      prev.includes(id) ? prev.filter((f) => f !== id) : [...prev, id]
    );
  }

  async function handleLaunch() {
    if (!task.trim()) {
      setErrorMsg("Please enter a task description.");
      return;
    }
    setErrorMsg(null);
    setIsLaunching(true);

    try {
      const res = await createRun({
        role,
        task,
        faults: selectedFaults,
        auto_approve: autoApprove,
        admin_token: adminToken || undefined,
      });

      router.push(`/runs/${res.run_id}`);
    } catch (err: any) {
      setErrorMsg(err.message || "Failed to launch run");
      setIsLaunching(false);
    }
  }

  return (
    <div className="space-y-8 max-w-6xl mx-auto">
      {/* Hero Platform Overview */}
      <div className="p-6 md:p-8 rounded-2xl bg-gradient-to-br from-slate-900 via-slate-900/90 to-blue-950/40 border border-slate-800 shadow-xl relative overflow-hidden">
        <div className="max-w-3xl space-y-3 relative z-10">
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-blue-500/10 border border-blue-500/20 text-blue-400 text-xs font-semibold">
            <Sparkles className="w-3.5 h-3.5" /> Autonomous AI Employee Runtime
          </div>
          <h1 className="text-2xl md:text-3xl font-extrabold text-white tracking-tight">
            CentrAlign Workforce Execution Console
          </h1>
          <p className="text-slate-300 text-sm md:text-base leading-relaxed">
            Deploy autonomous AI employees that reason, retrieve company policies, browse real internal ATS and Calendar web apps, verify candidate intent on messaging channels, and book interviews — backed by an independent ground-truth verifier.
          </p>
        </div>
      </div>

      {/* Main Task Form Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        {/* Left Column: Form (2 spans) */}
        <div className="lg:col-span-2 space-y-6">
          <div className="p-6 rounded-xl bg-slate-900/80 border border-slate-800 shadow-sm space-y-6">
            {/* Role Picker */}
            <div>
              <label className="block text-xs font-semibold uppercase tracking-wider text-slate-400 mb-2">
                1. Select AI Employee Role
              </label>
              <div className="grid grid-cols-2 gap-3">
                <button
                  type="button"
                  onClick={() => setRole("recruiter")}
                  className={`flex items-start gap-3 p-3.5 rounded-xl border text-left transition ${
                    role === "recruiter"
                      ? "bg-blue-600/15 border-blue-500 text-white shadow-sm shadow-blue-500/10"
                      : "bg-slate-950 border-slate-800 text-slate-400 hover:border-slate-700 hover:text-slate-200"
                  }`}
                >
                  <UserCheck className={`w-5 h-5 mt-0.5 ${role === "recruiter" ? "text-blue-400" : "text-slate-500"}`} />
                  <div>
                    <div className="font-semibold text-sm">Recruiter</div>
                    <div className="text-xs text-slate-400 mt-0.5">
                      Screens resumes, verifies intent on Telegram, schedules interviews in ATS & Calendar.
                    </div>
                  </div>
                </button>

                <button
                  type="button"
                  onClick={() => setRole("analyst")}
                  className={`flex items-start gap-3 p-3.5 rounded-xl border text-left transition ${
                    role === "analyst"
                      ? "bg-purple-600/15 border-purple-500 text-white shadow-sm shadow-purple-500/10"
                      : "bg-slate-950 border-slate-800 text-slate-400 hover:border-slate-700 hover:text-slate-200"
                  }`}
                >
                  <BarChart3 className={`w-5 h-5 mt-0.5 ${role === "analyst" ? "text-purple-400" : "text-slate-500"}`} />
                  <div>
                    <div className="font-semibold text-sm">Analyst (Read-Only)</div>
                    <div className="text-xs text-slate-400 mt-0.5">
                      Inspects candidate data and computes metrics. Write tools are blocked by permission layer.
                    </div>
                  </div>
                </button>
              </div>
            </div>

            {/* Example Chips */}
            <div>
              <label className="block text-xs font-semibold uppercase tracking-wider text-slate-400 mb-2">
                Quick Task Templates
              </label>
              <div className="flex flex-wrap gap-2">
                {EXAMPLE_TASKS.map((ex, i) => (
                  <button
                    key={i}
                    type="button"
                    onClick={() => handleSelectExample(ex)}
                    className="text-xs px-2.5 py-1.5 rounded-lg bg-slate-950 border border-slate-800 hover:border-blue-500/60 hover:text-blue-300 text-slate-300 transition flex items-center gap-1.5"
                  >
                    <Zap className="w-3 h-3 text-blue-400" /> {ex.label}
                  </button>
                ))}
              </div>
            </div>

            {/* Task Input Box */}
            <div>
              <label className="block text-xs font-semibold uppercase tracking-wider text-slate-400 mb-2">
                2. Task Instruction (Natural Language)
              </label>
              <textarea
                rows={4}
                value={task}
                onChange={(e) => setTask(e.target.value)}
                placeholder="Describe what the AI employee should accomplish in plain English..."
                className="w-full bg-slate-950 border border-slate-800 rounded-xl p-3.5 text-sm text-slate-100 placeholder-slate-600 focus:outline-none focus:border-blue-500 transition resize-y font-mono"
              />
            </div>

            {/* Fault Injection Toggles */}
            <div>
              <div className="flex items-center gap-2 mb-2">
                <Sliders className="w-4 h-4 text-amber-400" />
                <label className="text-xs font-semibold uppercase tracking-wider text-slate-400">
                  3. Fault Injection & Reliability Testing
                </label>
              </div>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-2.5">
                {FAULT_OPTIONS.map((f) => {
                  const active = selectedFaults.includes(f.id);
                  return (
                    <div
                      key={f.id}
                      onClick={() => toggleFault(f.id)}
                      className={`p-3 rounded-lg border cursor-pointer select-none transition flex items-start gap-2.5 ${
                        active
                          ? "bg-amber-950/20 border-amber-600/50 text-slate-100"
                          : "bg-slate-950/60 border-slate-800/80 text-slate-400 hover:border-slate-700"
                      }`}
                    >
                      <input
                        type="checkbox"
                        checked={active}
                        onChange={() => {}}
                        className="mt-0.5 rounded border-slate-700 text-blue-600 focus:ring-0 cursor-pointer"
                      />
                      <div className="text-xs">
                        <div className="font-medium text-slate-200">{f.name}</div>
                        <div className="text-[11px] text-slate-500 mt-0.5">{f.desc}</div>
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>

            {/* Execution Controls */}
            <div className="pt-2 border-t border-slate-800 flex flex-wrap items-center justify-between gap-4">
              <label className="flex items-center gap-2.5 text-xs text-slate-300 cursor-pointer select-none">
                <input
                  type="checkbox"
                  checked={autoApprove}
                  onChange={(e) => setAutoApprove(e.target.checked)}
                  className="rounded border-slate-700 text-blue-600 focus:ring-0"
                />
                <span>
                  <strong>Auto-Approve Actions</strong> (Uncheck to test human escalation & manager approval card)
                </span>
              </label>

              <div className="flex items-center gap-2">
                <button
                  type="button"
                  disabled={isLaunching}
                  onClick={handleLaunch}
                  className="inline-flex items-center gap-2 px-5 py-2.5 rounded-xl bg-blue-600 hover:bg-blue-500 disabled:bg-blue-800 font-semibold text-sm text-white shadow-lg shadow-blue-600/25 transition cursor-pointer"
                >
                  {isLaunching ? (
                    <>
                      <div className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                      Launching Run...
                    </>
                  ) : (
                    <>
                      <Play className="w-4 h-4 fill-current" /> Launch Agent Run
                    </>
                  )}
                </button>
              </div>
            </div>

            {errorMsg && (
              <div className="p-3 rounded-lg bg-red-950/40 border border-red-800 text-red-300 text-xs flex items-center gap-2">
                <AlertTriangle className="w-4 h-4 flex-shrink-0" />
                <span>{errorMsg}</span>
              </div>
            )}
          </div>
        </div>

        {/* Right Column: Platform Architecture & Recent Runs */}
        <div className="space-y-6">
          {/* Architecture Mapping Card */}
          <div className="p-5 rounded-xl bg-slate-900/60 border border-slate-800 space-y-3">
            <h3 className="text-xs font-semibold uppercase tracking-wider text-slate-400 flex items-center gap-1.5">
              <ShieldCheck className="w-4 h-4 text-blue-400" /> Platform Architecture
            </h3>
            <div className="space-y-2 text-xs">
              <div className="flex justify-between py-1 border-b border-slate-800/80">
                <span className="text-slate-400">Reasoning Engine</span>
                <span className="font-medium text-slate-200">Gemini Function Calling Loop</span>
              </div>
              <div className="flex justify-between py-1 border-b border-slate-800/80">
                <span className="text-slate-400">Workflow Engine</span>
                <span className="font-medium text-slate-200">Role Playbooks (roles/*.yaml)</span>
              </div>
              <div className="flex justify-between py-1 border-b border-slate-800/80">
                <span className="text-slate-400">Company Memory</span>
                <span className="font-medium text-slate-200">Postgres facts + summary</span>
              </div>
              <div className="flex justify-between py-1 border-b border-slate-800/80">
                <span className="text-slate-400">Knowledge Retrieval</span>
                <span className="font-medium text-slate-200">Full-text policy search</span>
              </div>
              <div className="flex justify-between py-1 border-b border-slate-800/80">
                <span className="text-slate-400">Permission Layer</span>
                <span className="font-medium text-slate-200">Pre-execution interceptor</span>
              </div>
              <div className="flex justify-between py-1 border-b border-slate-800/80">
                <span className="text-slate-400">Human Escalation</span>
                <span className="font-medium text-slate-200">ask_user & request_approval</span>
              </div>
              <div className="flex justify-between py-1">
                <span className="text-slate-400">Ground-Truth Verifier</span>
                <span className="font-medium text-slate-200">Postgres state inspector</span>
              </div>
            </div>
          </div>

          {/* Recent Runs List */}
          <div className="p-5 rounded-xl bg-slate-900/60 border border-slate-800 space-y-3">
            <div className="flex items-center justify-between">
              <h3 className="text-xs font-semibold uppercase tracking-wider text-slate-400 flex items-center gap-1.5">
                <Clock className="w-4 h-4 text-slate-400" /> Recent Agent Runs
              </h3>
              <button
                type="button"
                onClick={loadRuns}
                className="text-[11px] text-blue-400 hover:underline"
              >
                Refresh
              </button>
            </div>

            {isLoadingRuns ? (
              <div className="py-8 text-center text-xs text-slate-500">Loading recent runs...</div>
            ) : recentRuns.length === 0 ? (
              <div className="py-8 text-center text-xs text-slate-500">No runs executed yet.</div>
            ) : (
              <div className="space-y-2">
                {recentRuns.map((r) => {
                  const isCompleted = r.status === "completed";
                  const isRunning = r.status === "running";
                  return (
                    <Link
                      key={r.id}
                      href={`/runs/${r.id}`}
                      className="block p-2.5 rounded-lg bg-slate-950 border border-slate-850 hover:border-slate-700 transition group"
                    >
                      <div className="flex items-center justify-between text-xs mb-1">
                        <span className="font-mono text-slate-400 text-[11px]">
                          {r.id.slice(0, 8)}...
                        </span>
                        <span
                          className={`px-1.5 py-0.5 rounded text-[10px] font-semibold uppercase ${
                            isCompleted
                              ? "bg-emerald-950/60 text-emerald-400 border border-emerald-800/40"
                              : isRunning
                              ? "bg-blue-950/60 text-blue-400 border border-blue-800/40 animate-pulse"
                              : "bg-amber-950/60 text-amber-400 border border-amber-800/40"
                          }`}
                        >
                          {r.status}
                        </span>
                      </div>
                      <div className="text-xs text-slate-300 font-medium truncate group-hover:text-blue-300 transition">
                        {r.task}
                      </div>
                    </Link>
                  );
                })}
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
