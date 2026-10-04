"use client";

import Link from "next/link";
import { API_BASE } from "@/lib/api";
import { ExternalLink, ArrowLeft, Globe, Calendar, Key, Shield, AlertCircle } from "lucide-react";

export default function SandboxPage() {
  return (
    <div className="space-y-8 max-w-5xl mx-auto">
      <div>
        <div className="flex items-center gap-2 mb-1">
          <Link href="/" className="text-xs text-slate-400 hover:text-white inline-flex items-center gap-1 transition">
            <ArrowLeft className="w-3.5 h-3.5" /> Console
          </Link>
        </div>
        <h1 className="text-2xl font-bold text-white tracking-tight flex items-center gap-2.5">
          <Globe className="w-6 h-6 text-blue-400" /> Internal Company Sandbox Applications
        </h1>
        <p className="text-xs text-slate-400 mt-1">
          Two real server-rendered web applications hosted in the FastAPI backend where the AI employees work.
        </p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* ATS Sandbox Card */}
        <div className="p-6 rounded-xl bg-slate-900/80 border border-slate-800 shadow-sm space-y-4 flex flex-col justify-between">
          <div className="space-y-3">
            <div className="flex items-center justify-between">
              <span className="p-2.5 rounded-lg bg-blue-600/10 border border-blue-500/20 text-blue-400">
                <Globe className="w-5 h-5" />
              </span>
              <span className="text-xs font-semibold px-2 py-0.5 rounded bg-slate-800 text-slate-300">
                Port: 8000
              </span>
            </div>
            <h2 className="text-lg font-bold text-white">CentrAlign ATS (Applicant Tracking System)</h2>
            <p className="text-xs text-slate-300 leading-relaxed">
              Manages job requisitions, candidate resume texts, pipeline stage transitions (Applied &rarr; Shortlisted &rarr; Intent Confirmed &rarr; Interview Scheduled), and candidate intent records (notice period, expected CTC in LPA).
            </p>

            <div className="p-3 rounded-lg bg-slate-950 border border-slate-850 font-mono text-xs space-y-1 text-slate-400">
              <div className="text-slate-300 font-semibold mb-1 flex items-center gap-1.5">
                <Key className="w-3.5 h-3.5 text-amber-400" /> Demo Credentials (in Vault):
              </div>
              <div>Username: <strong className="text-slate-200">recruiter_admin</strong></div>
              <div>Password: <strong className="text-slate-200">ats_secret_2026</strong></div>
              <div>Path: <span className="text-blue-400">/sandbox/ats/</span></div>
            </div>
          </div>

          <a
            href={`${API_BASE}/sandbox/ats/`}
            target="_blank"
            rel="noreferrer"
            className="inline-flex items-center justify-center gap-2 w-full py-2.5 rounded-lg bg-blue-600 hover:bg-blue-500 font-semibold text-xs text-white transition shadow-md shadow-blue-900/20"
          >
            Open ATS Sandbox in New Tab <ExternalLink className="w-3.5 h-3.5" />
          </a>
        </div>

        {/* Calendar Sandbox Card */}
        <div className="p-6 rounded-xl bg-slate-900/80 border border-slate-800 shadow-sm space-y-4 flex flex-col justify-between">
          <div className="space-y-3">
            <div className="flex items-center justify-between">
              <span className="p-2.5 rounded-lg bg-purple-600/10 border border-purple-500/20 text-purple-400">
                <Calendar className="w-5 h-5" />
              </span>
              <span className="text-xs font-semibold px-2 py-0.5 rounded bg-slate-800 text-slate-300">
                Port: 8000
              </span>
            </div>
            <h2 className="text-lg font-bold text-white">CentrAlign Interview Calendar</h2>
            <p className="text-xs text-slate-300 leading-relaxed">
              Maintains interviewer calendar schedules, 45-minute weekday interview slots, and booking confirmations. Enforces strict rules: no double-booking and prerequisite &quot;Intent Confirmed&quot; stage.
            </p>

            <div className="p-3 rounded-lg bg-slate-950 border border-slate-850 font-mono text-xs space-y-1 text-slate-400">
              <div className="text-slate-300 font-semibold mb-1 flex items-center gap-1.5">
                <Key className="w-3.5 h-3.5 text-amber-400" /> Demo Credentials (in Vault):
              </div>
              <div>Username: <strong className="text-slate-200">calendar_admin</strong></div>
              <div>Password: <strong className="text-slate-200">cal_secret_2026</strong></div>
              <div>Path: <span className="text-purple-400">/sandbox/calendar/</span></div>
            </div>
          </div>

          <a
            href={`${API_BASE}/sandbox/calendar/`}
            target="_blank"
            rel="noreferrer"
            className="inline-flex items-center justify-center gap-2 w-full py-2.5 rounded-lg bg-purple-600 hover:bg-purple-500 font-semibold text-xs text-white transition shadow-md shadow-purple-900/20"
          >
            Open Calendar Sandbox in New Tab <ExternalLink className="w-3.5 h-3.5" />
          </a>
        </div>
      </div>
    </div>
  );
}
