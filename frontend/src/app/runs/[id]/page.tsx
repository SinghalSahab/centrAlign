"use client";

import { useEffect, useState, useRef } from "react";
import { useParams, useRouter } from "next/navigation";
import Link from "next/link";
import { 
  API_BASE, 
  getRunDetail, 
  approveRunAction, 
  replyToRun, 
  RunDetailResponse, 
  Step 
} from "@/lib/api";
import { 
  CheckCircle2, 
  XCircle, 
  Clock, 
  ShieldCheck, 
  ShieldAlert, 
  AlertTriangle, 
  ArrowLeft, 
  MessageSquare, 
  Database, 
  Send, 
  Check, 
  X, 
  Globe, 
  FileText, 
  Key, 
  Search, 
  Layers, 
  RotateCw,
  Sparkles,
  ChevronDown,
  ChevronRight
} from "lucide-react";

export default function RunInspectorPage() {
  const params = useParams();
  const runId = params.id as string;
  const router = useRouter();

  const [data, setData] = useState<RunDetailResponse | null>(null);
  const [steps, setSteps] = useState<Step[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [activeTab, setActiveTab] = useState<"timeline" | "memory" | "messages" | "audit">("timeline");
  
  // Escalation & Approval state
  const [userReplyText, setUserReplyText] = useState("");
  const [isSubmittingApproval, setIsSubmittingApproval] = useState(false);

  // Expanded steps map
  const [expandedSteps, setExpandedSteps] = useState<Record<number, boolean>>({});

  const sseRef = useRef<EventSource | null>(null);

  useEffect(() => {
    // Initial fetch
    loadData();

    // Setup SSE streaming
    const eventSource = new EventSource(`${API_BASE}/api/runs/${runId}/events`);
    sseRef.current = eventSource;

    eventSource.addEventListener("step", (e) => {
      try {
        const step = JSON.parse(e.data);
        setSteps((prev) => {
          if (prev.some((s) => s.step_number === step.step_number)) {
            return prev.map((s) => (s.step_number === step.step_number ? step : s));
          }
          return [...prev, step];
        });
      } catch (err) {
        console.error("SSE step parse error", err);
      }
    });

    eventSource.addEventListener("verified", (e) => {
      try {
        const v = JSON.parse(e.data);
        setData((prev) => prev ? { ...prev, verification: v } : null);
      } catch (err) {
        console.error("SSE verified parse error", err);
      }
    });

    eventSource.addEventListener("completed", () => {
      loadData();
    });

    eventSource.onerror = () => {
      // Fallback to polling if SSE drops
      loadData();
    };

    const interval = setInterval(loadData, 5000);

    return () => {
      eventSource.close();
      clearInterval(interval);
    };
  }, [runId]);

  async function loadData() {
    try {
      const res = await getRunDetail(runId);
      setData(res);
      setSteps(res.steps || []);
    } catch (e) {
      console.error("Error loading run details", e);
    } finally {
      setIsLoading(false);
    }
  }

  function toggleStepExpand(num: number) {
    setExpandedSteps((prev) => ({ ...prev, [num]: !prev[num] }));
  }

  async function handleApprove(approvalId: number, decision: "approved" | "rejected") {
    setIsSubmittingApproval(true);
    try {
      await approveRunAction(runId, approvalId, decision);
      await loadData();
    } catch (e) {
      console.error(e);
    } finally {
      setIsSubmittingApproval(false);
    }
  }

  async function handleSendReply() {
    if (!userReplyText.trim()) return;
    try {
      await replyToRun(runId, userReplyText);
      setUserReplyText("");
      await loadData();
    } catch (e) {
      console.error(e);
    }
  }

  if (isLoading && !data) {
    return (
      <div className="py-20 text-center space-y-3">
        <div className="w-8 h-8 border-2 border-blue-500 border-t-transparent rounded-full animate-spin mx-auto" />
        <div className="text-sm text-slate-400">Loading Agent Run #{runId.slice(0, 8)}...</div>
      </div>
    );
  }

  if (!data) {
    return (
      <div className="py-20 text-center space-y-4">
        <AlertTriangle className="w-10 h-10 text-amber-500 mx-auto" />
        <h2 className="text-lg font-bold text-white">Run Not Found</h2>
        <Link href="/" className="inline-flex items-center gap-1.5 text-sm text-blue-400 hover:underline">
          <ArrowLeft className="w-4 h-4" /> Back to Console
        </Link>
      </div>
    );
  }

  const run = data.run;
  const verification = data.verification;
  const isCompleted = run.status === "completed";
  const isRunning = run.status === "running";
  const isWaitingApproval = run.status === "waiting_approval";
  const pendingApproval = data.approvals.find((a) => a.status === "pending");

  // Format Tool Icon
  function getToolIcon(name?: string) {
    if (!name) return <Layers className="w-3.5 h-3.5" />;
    if (name.startsWith("web_")) return <Globe className="w-3.5 h-3.5 text-blue-400" />;
    if (name === "get_credentials") return <Key className="w-3.5 h-3.5 text-amber-400" />;
    if (name === "knowledge_search") return <Search className="w-3.5 h-3.5 text-purple-400" />;
    if (name.startsWith("memory_")) return <Database className="w-3.5 h-3.5 text-cyan-400" />;
    if (name.includes("candidate") || name.includes("reply")) return <MessageSquare className="w-3.5 h-3.5 text-emerald-400" />;
    if (name === "finish") return <CheckCircle2 className="w-3.5 h-3.5 text-green-400" />;
    return <Layers className="w-3.5 h-3.5 text-slate-400" />;
  }

  return (
    <div className="space-y-6 max-w-7xl mx-auto">
      {/* Top Header */}
      <div className="flex flex-wrap items-center justify-between gap-4 pb-4 border-b border-slate-800">
        <div className="space-y-1">
          <div className="flex items-center gap-3">
            <Link href="/" className="text-xs text-slate-400 hover:text-white inline-flex items-center gap-1 transition">
              <ArrowLeft className="w-3.5 h-3.5" /> Console
            </Link>
            <span className="text-slate-600">&bull;</span>
            <span className="text-xs font-mono text-slate-400">Run ID: {run.id}</span>
          </div>
          <h1 className="text-xl md:text-2xl font-bold text-white tracking-tight flex items-center gap-3">
            <span>{run.task}</span>
          </h1>
        </div>

        <div className="flex items-center gap-3">
          {/* Role Badge */}
          <span className="px-2.5 py-1 rounded-full text-xs font-semibold uppercase bg-slate-900 border border-slate-700 text-slate-200">
            Role: {run.role}
          </span>

          {/* Status Badge */}
          <div
            className={`px-3 py-1 rounded-full text-xs font-bold uppercase tracking-wider border flex items-center gap-1.5 ${
              isCompleted
                ? "bg-emerald-950/60 text-emerald-400 border-emerald-800/60"
                : isRunning
                ? "bg-blue-950/60 text-blue-400 border-blue-800/60 animate-pulse"
                : isWaitingApproval
                ? "bg-amber-950/60 text-amber-400 border-amber-800/60"
                : "bg-red-950/60 text-red-400 border-red-800/60"
            }`}
          >
            {isCompleted && <CheckCircle2 className="w-3.5 h-3.5" />}
            {isRunning && <RotateCw className="w-3.5 h-3.5 animate-spin" />}
            {isWaitingApproval && <AlertTriangle className="w-3.5 h-3.5" />}
            <span>{run.status.replace("_", " ")}</span>
          </div>
        </div>
      </div>

      {/* Main 2-Column Inspector Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
        {/* Left Column: Live Step Timeline & Escalation (7 cols) */}
        <div className="lg:col-span-7 space-y-6">
          {/* Human Escalation / Manager Approval Card */}
          {isWaitingApproval && pendingApproval && (
            <div className="p-5 rounded-xl bg-amber-950/30 border border-amber-500/50 shadow-lg shadow-amber-950/20 space-y-4">
              <div className="flex items-center gap-2 text-amber-400 font-semibold text-sm">
                <AlertTriangle className="w-4 h-4" /> Manager Approval Required (Safety Gate)
              </div>
              <div className="text-xs text-slate-300">
                The agent requested to perform a sensitive write operation that requires explicit manager approval:
              </div>
              <div className="p-3 rounded-lg bg-slate-950 border border-amber-900/60 font-mono text-xs text-amber-200 space-y-1">
                <div><strong>Tool:</strong> {pendingApproval.tool_name}</div>
                <div><strong>Reason:</strong> {pendingApproval.reason}</div>
                <div><strong>Parameters:</strong> {JSON.stringify(pendingApproval.tool_args)}</div>
              </div>
              <div className="flex items-center gap-3 pt-1">
                <button
                  type="button"
                  disabled={isSubmittingApproval}
                  onClick={() => handleApprove(pendingApproval.id, "approved")}
                  className="px-4 py-2 rounded-lg bg-emerald-600 hover:bg-emerald-500 text-white font-semibold text-xs flex items-center gap-1.5 shadow-md shadow-emerald-900/20 transition cursor-pointer"
                >
                  <Check className="w-4 h-4" /> Authorize Action
                </button>
                <button
                  type="button"
                  disabled={isSubmittingApproval}
                  onClick={() => handleApprove(pendingApproval.id, "rejected")}
                  className="px-4 py-2 rounded-lg bg-red-600/80 hover:bg-red-500 text-white font-semibold text-xs flex items-center gap-1.5 transition cursor-pointer"
                >
                  <X className="w-4 h-4" /> Reject Request
                </button>
              </div>
            </div>
          )}

          {/* User Clarification Box if needed */}
          {run.status === "waiting_user" && (
            <div className="p-5 rounded-xl bg-blue-950/30 border border-blue-500/50 shadow-lg space-y-3">
              <div className="text-blue-400 font-semibold text-sm flex items-center gap-2">
                <MessageSquare className="w-4 h-4" /> Agent Requested Clarification
              </div>
              <div className="flex items-center gap-2">
                <input
                  type="text"
                  value={userReplyText}
                  onChange={(e) => setUserReplyText(e.target.value)}
                  placeholder="Provide clarification, e.g. 'Please review Senior Backend Engineer role'..."
                  className="flex-1 bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-xs text-white focus:outline-none focus:border-blue-500"
                />
                <button
                  type="button"
                  onClick={handleSendReply}
                  className="px-3.5 py-2 bg-blue-600 hover:bg-blue-500 text-white text-xs font-semibold rounded-lg flex items-center gap-1 cursor-pointer"
                >
                  <Send className="w-3.5 h-3.5" /> Send
                </button>
              </div>
            </div>
          )}

          {/* Timeline Container */}
          <div className="p-5 rounded-xl bg-slate-900/70 border border-slate-800 space-y-4">
            <div className="flex items-center justify-between pb-3 border-b border-slate-800">
              <h2 className="text-xs font-semibold uppercase tracking-wider text-slate-400 flex items-center gap-2">
                <Clock className="w-4 h-4 text-blue-400" /> Execution Step Timeline ({steps.length} Steps)
              </h2>
              {isRunning && (
                <span className="flex items-center gap-1.5 text-xs text-blue-400 font-medium">
                  <span className="w-2 h-2 rounded-full bg-blue-400 animate-ping" /> Live Streaming (SSE)
                </span>
              )}
            </div>

            {steps.length === 0 ? (
              <div className="py-12 text-center text-xs text-slate-500">
                Agent is initializing environment and observing initial state...
              </div>
            ) : (
              <div className="space-y-3">
                {steps.map((s) => {
                  const isExpanded = !!expandedSteps[s.step_number];
                  const hasError = !!s.error;
                  const isFinish = s.action_type === "finish";
                  const isDenial = s.action_type === "denial";

                  return (
                    <div
                      key={s.step_number}
                      className={`rounded-xl border transition p-4 ${
                        isFinish
                          ? "bg-emerald-950/15 border-emerald-800/40"
                          : hasError || isDenial
                          ? "bg-red-950/15 border-red-800/40"
                          : "bg-slate-950/70 border-slate-850 hover:border-slate-750"
                      }`}
                    >
                      <div className="flex items-start justify-between gap-3">
                        <div className="flex items-center gap-2.5">
                          <span className="w-6 h-6 rounded-md bg-slate-900 border border-slate-800 flex items-center justify-center font-mono text-xs font-semibold text-slate-300">
                            {s.step_number}
                          </span>

                          <span
                            className={`px-2 py-0.5 rounded text-[10px] font-bold uppercase tracking-wider ${
                              isFinish
                                ? "bg-emerald-950 text-emerald-400 border border-emerald-800/60"
                                : isDenial
                                ? "bg-amber-950 text-amber-400 border border-amber-800/60"
                                : hasError
                                ? "bg-red-950 text-red-400 border border-red-800/60"
                                : "bg-slate-900 text-slate-300 border border-slate-800"
                            }`}
                          >
                            {s.action_type}
                          </span>

                          {s.tool_name && (
                            <div className="flex items-center gap-1.5 text-xs font-mono font-medium text-slate-200">
                              {getToolIcon(s.tool_name)}
                              <span>{s.tool_name}</span>
                            </div>
                          )}
                        </div>

                        {s.observation && (
                          <button
                            type="button"
                            onClick={() => toggleStepExpand(s.step_number)}
                            className="text-[11px] text-slate-400 hover:text-white flex items-center gap-1"
                          >
                            {isExpanded ? "Collapse" : "Snapshot"}
                            {isExpanded ? <ChevronDown className="w-3.5 h-3.5" /> : <ChevronRight className="w-3.5 h-3.5" />}
                          </button>
                        )}
                      </div>

                      {/* Tool Parameters */}
                      {s.tool_args && Object.keys(s.tool_args).length > 0 && (
                        <div className="mt-2.5 text-xs font-mono text-slate-400 bg-slate-900/60 px-3 py-1.5 rounded-lg border border-slate-850 overflow-x-auto">
                          {JSON.stringify(s.tool_args)}
                        </div>
                      )}

                      {/* Error & Self-Healing Strategy */}
                      {hasError && (
                        <div className="mt-2.5 p-3 rounded-lg bg-red-950/30 border border-red-800/50 text-xs space-y-1">
                          <div className="text-red-300 font-semibold flex items-center gap-1.5">
                            <AlertTriangle className="w-3.5 h-3.5 flex-shrink-0" />
                            <span>Category: {s.error}</span>
                          </div>
                          {s.recovery_action && (
                            <div className="text-slate-300 text-[11px]">
                              <strong>Recovery Strategy:</strong> {s.recovery_action}
                            </div>
                          )}
                        </div>
                      )}

                      {/* Compact Snapshot Observation (Collapsible) */}
                      {s.observation && isExpanded && (
                        <div className="mt-3 p-3 rounded-lg bg-slate-900/90 border border-slate-800 text-xs text-slate-300 font-mono whitespace-pre-wrap max-h-80 overflow-y-auto">
                          {s.observation}
                        </div>
                      )}
                    </div>
                  );
                })}
              </div>
            )}
          </div>
        </div>

        {/* Right Column: Verification, Memory, Messages & Audit (5 cols) */}
        <div className="lg:col-span-5 space-y-6">
          {/* Verification Badge & Evidence Card */}
          <div className="p-5 rounded-xl bg-slate-900/80 border border-slate-800 shadow-md space-y-4">
            <div className="flex items-center justify-between pb-3 border-b border-slate-800">
              <h2 className="text-xs font-semibold uppercase tracking-wider text-slate-400 flex items-center gap-1.5">
                <ShieldCheck className="w-4 h-4 text-emerald-400" /> Independent Ground-Truth Verifier
              </h2>
              {verification && (
                <span
                  className={`px-2.5 py-0.5 rounded-full text-[11px] font-bold uppercase tracking-wider ${
                    verification.all_passed
                      ? "bg-emerald-950 text-emerald-300 border border-emerald-700/60"
                      : "bg-red-950 text-red-300 border border-red-700/60"
                  }`}
                >
                  {verification.all_passed ? "100% Verified" : "Verification Failed"}
                </span>
              )}
            </div>

            {!verification ? (
              <div className="py-6 text-center text-xs text-slate-500">
                {isCompleted
                  ? "Ground truth verification in progress..."
                  : "Verifier will inspect Postgres state independently after the agent finishes."}
              </div>
            ) : (
              <div className="space-y-2.5">
                <div className="flex items-center justify-between text-xs text-slate-400 pb-1">
                  <span>Direct Database Checks:</span>
                  <span className="font-semibold text-slate-200">
                    {verification.passed_checks} / {verification.total_checks} Passed
                  </span>
                </div>

                <div className="space-y-2">
                  {verification.check_results.map((c, i) => (
                    <div
                      key={i}
                      className={`p-3 rounded-lg border text-xs space-y-1 ${
                        c.passed
                          ? "bg-emerald-950/20 border-emerald-900/50"
                          : "bg-red-950/20 border-red-900/50"
                      }`}
                    >
                      <div className="flex items-center justify-between font-mono font-semibold">
                        <span className={c.passed ? "text-emerald-300" : "text-red-300"}>
                          {c.type}
                        </span>
                        {c.passed ? (
                          <span className="flex items-center gap-1 text-[11px] text-emerald-400">
                            <CheckCircle2 className="w-3.5 h-3.5" /> PASS
                          </span>
                        ) : (
                          <span className="flex items-center gap-1 text-[11px] text-red-400">
                            <XCircle className="w-3.5 h-3.5" /> FAIL
                          </span>
                        )}
                      </div>
                      <div className="text-[11px] text-slate-300">
                        {c.evidence || c.error}
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>

          {/* Secondary Information Tabs (Memory, Telegram, Audit) */}
          <div className="p-5 rounded-xl bg-slate-900/80 border border-slate-800 shadow-md space-y-4">
            <div className="flex items-center gap-2 border-b border-slate-800 pb-2">
              <button
                type="button"
                onClick={() => setActiveTab("timeline")}
                className={`text-xs font-semibold px-2.5 py-1 rounded-md transition ${
                  activeTab === "timeline" ? "bg-slate-800 text-white" : "text-slate-400 hover:text-slate-200"
                }`}
              >
                Executive Summary
              </button>
              <button
                type="button"
                onClick={() => setActiveTab("memory")}
                className={`text-xs font-semibold px-2.5 py-1 rounded-md transition ${
                  activeTab === "memory" ? "bg-slate-800 text-white" : "text-slate-400 hover:text-slate-200"
                }`}
              >
                Memory ({data.memory_facts.length})
              </button>
              <button
                type="button"
                onClick={() => setActiveTab("messages")}
                className={`text-xs font-semibold px-2.5 py-1 rounded-md transition ${
                  activeTab === "messages" ? "bg-slate-800 text-white" : "text-slate-400 hover:text-slate-200"
                }`}
              >
                Candidate Chat ({data.messages.length})
              </button>
              <button
                type="button"
                onClick={() => setActiveTab("audit")}
                className={`text-xs font-semibold px-2.5 py-1 rounded-md transition ${
                  activeTab === "audit" ? "bg-slate-800 text-white" : "text-slate-400 hover:text-slate-200"
                }`}
              >
                Audit Log ({data.audit_logs.length})
              </button>
            </div>

            {/* Tab: Summary */}
            {activeTab === "timeline" && (
              <div className="space-y-3 text-xs">
                {run.summary ? (
                  <div className="p-3.5 rounded-lg bg-slate-950 border border-slate-850 text-slate-200 leading-relaxed">
                    {run.summary}
                  </div>
                ) : (
                  <div className="py-6 text-center text-slate-500">Summary will appear upon task completion.</div>
                )}
              </div>
            )}

            {/* Tab: Memory Facts */}
            {activeTab === "memory" && (
              <div className="space-y-2">
                {data.memory_facts.length === 0 ? (
                  <div className="py-6 text-center text-xs text-slate-500">No memory facts stored yet.</div>
                ) : (
                  data.memory_facts.map((f, i) => (
                    <div key={i} className="p-2.5 rounded-lg bg-slate-950 border border-slate-850 text-xs">
                      <div className="font-semibold text-blue-400">{f.key}</div>
                      <div className="text-slate-300 font-mono mt-0.5 text-[11px] whitespace-pre-wrap">
                        {typeof f.value === "object" ? JSON.stringify(f.value) : f.value}
                      </div>
                    </div>
                  ))
                )}
              </div>
            )}

            {/* Tab: Candidate Chat */}
            {activeTab === "messages" && (
              <div className="space-y-2.5 max-h-72 overflow-y-auto">
                {data.messages.length === 0 ? (
                  <div className="py-6 text-center text-xs text-slate-500">No Telegram candidate messages sent yet.</div>
                ) : (
                  data.messages.map((m, i) => {
                    const isOutbound = m.direction === "outbound";
                    return (
                      <div
                        key={i}
                        className={`flex flex-col ${isOutbound ? "items-end" : "items-start"}`}
                      >
                        <div
                          className={`max-w-[85%] p-2.5 rounded-xl text-xs ${
                            isOutbound
                              ? "bg-blue-600 text-white rounded-br-sm"
                              : "bg-slate-800 text-slate-100 rounded-bl-sm"
                          }`}
                        >
                          <div className="text-[10px] opacity-75 font-semibold mb-0.5">
                            {isOutbound ? "AI Recruiter (Telegram)" : "Candidate"}
                          </div>
                          <div>{m.text}</div>
                        </div>
                      </div>
                    );
                  })
                )}
              </div>
            )}

            {/* Tab: Audit Log */}
            {activeTab === "audit" && (
              <div className="space-y-2">
                {data.audit_logs.length === 0 ? (
                  <div className="py-6 text-center text-xs text-slate-500">No security audit events logged.</div>
                ) : (
                  data.audit_logs.map((al, i) => (
                    <div key={i} className="p-2.5 rounded-lg bg-slate-950 border border-slate-850 text-xs space-y-0.5">
                      <div className="flex items-center justify-between">
                        <span className="font-bold text-amber-400 font-mono">{al.event_type}</span>
                        <span className="text-[10px] text-slate-500">{al.created_at}</span>
                      </div>
                      <div className="text-slate-300 font-mono text-[11px]">
                        {JSON.stringify(al.details)}
                      </div>
                    </div>
                  ))
                )}
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
