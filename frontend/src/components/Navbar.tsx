"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { API_BASE, fetchHealth } from "@/lib/api";
import { Cpu, CheckCircle2, AlertCircle, ExternalLink, Activity } from "lucide-react";

export default function Navbar() {
  const [health, setHealth] = useState<{ status: string; gemini_model?: string } | null>(null);

  useEffect(() => {
    fetchHealth().then((h) => setHealth(h));
    const interval = setInterval(() => {
      fetchHealth().then((h) => setHealth(h));
    }, 15000);
    return () => clearInterval(interval);
  }, []);

  const isHealthy = health?.status === "healthy";

  return (
    <header className="border-b border-slate-800 bg-slate-950/80 backdrop-blur sticky top-0 z-50 text-slate-100">
      <div className="max-w-7xl mx-auto px-4 h-16 flex items-center justify-between">
        <div className="flex items-center gap-6">
          <Link href="/" className="flex items-center gap-2.5 font-bold text-lg tracking-tight text-white hover:opacity-90 transition">
            <div className="w-8 h-8 rounded-lg bg-blue-600 flex items-center justify-center text-white shadow-lg shadow-blue-500/20">
              <Cpu className="w-5 h-5" />
            </div>
            <span>Centr<span className="text-blue-400">Align</span></span>
            <span className="text-xs font-semibold px-2 py-0.5 rounded-full bg-slate-800 text-slate-300 border border-slate-700">
              AI Workforce Layer
            </span>
          </Link>

          <nav className="hidden md:flex items-center gap-1 text-sm font-medium text-slate-400">
            <Link href="/" className="px-3 py-1.5 rounded-md hover:text-white hover:bg-slate-850 transition">
              Console
            </Link>
            <Link href="/evals" className="px-3 py-1.5 rounded-md hover:text-white hover:bg-slate-850 transition">
              Benchmarks & Evals
            </Link>
            <Link href="/sandbox" className="px-3 py-1.5 rounded-md hover:text-white hover:bg-slate-850 transition">
              Sandbox Apps
            </Link>
          </nav>
        </div>

        <div className="flex items-center gap-3 text-xs">
          <a
            href={`${API_BASE}/sandbox/ats/`}
            target="_blank"
            rel="noreferrer"
            className="hidden sm:inline-flex items-center gap-1 px-2.5 py-1 rounded bg-slate-900 border border-slate-800 text-slate-300 hover:text-white hover:border-slate-700 transition"
          >
            ATS Sandbox <ExternalLink className="w-3 h-3 text-slate-400" />
          </a>
          <a
            href={`${API_BASE}/sandbox/calendar/`}
            target="_blank"
            rel="noreferrer"
            className="hidden sm:inline-flex items-center gap-1 px-2.5 py-1 rounded bg-slate-900 border border-slate-800 text-slate-300 hover:text-white hover:border-slate-700 transition"
          >
            Calendar Sandbox <ExternalLink className="w-3 h-3 text-slate-400" />
          </a>

          <div
            className={`flex items-center gap-1.5 px-2.5 py-1 rounded-full border ${
              isHealthy
                ? "bg-emerald-950/40 border-emerald-800/60 text-emerald-300"
                : "bg-amber-950/40 border-amber-800/60 text-amber-300"
            }`}
            title={`Backend: ${API_BASE}`}
          >
            {isHealthy ? <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400" /> : <Activity className="w-3.5 h-3.5 animate-spin" />}
            <span className="font-medium">{isHealthy ? "Runtime Active" : "Connecting..."}</span>
          </div>
        </div>
      </div>
    </header>
  );
}
