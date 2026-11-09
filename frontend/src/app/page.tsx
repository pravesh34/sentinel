"use client";
import { useEffect, useState } from "react";
import { api, login as apiLogin } from "@/lib/api";
import { BarChart, Bar, XAxis, YAxis, Tooltip } from "recharts";

type Exec = { id: string; objective: string; status: string; total_cost: number; total_tokens: number };
type Tool = { tool_id: string; name: string; description: string; risk_level: string; enabled: boolean };
type Approval = { id: string; execution_id: string; tool_id: string; risk_level: string; status: string };

export default function Page() {
  const [email, setEmail] = useState("demo@example.com");
  const [password, setPassword] = useState("password123");
  const [loggedIn, setLoggedIn] = useState(false);
  const [objective, setObjective] = useState("Research the latest developments in agentic AI, compare five frameworks, summarize their advantages");
  const [mode, setMode] = useState("supervised");
  const [maxSteps, setMaxSteps] = useState(20);
  const [maxCost, setMaxCost] = useState(1.0);
  const [overview, setOverview] = useState<any>(null);
  const [execs, setExecs] = useState<Exec[]>([]);
  const [tools, setTools] = useState<Tool[]>([]);
  const [approvals, setApprovals] = useState<Approval[]>([]);
  const [trace, setTrace] = useState<any>(null);
  const [msg, setMsg] = useState("");

  async function refresh() {
    if (!loggedIn) return;
    try {
      setOverview(await api("/api/v1/analytics/overview"));
      setExecs(await api("/api/v1/executions"));
      setTools(await api("/api/v1/tools"));
      setApprovals(await api("/api/v1/approvals"));
    } catch (e: any) { setMsg(String(e.message || e)); }
  }
  useEffect(() => { refresh(); }, [loggedIn]);
  // Poll live (WS fallback: polling /trace). In prod use ws://.../ws/executions/{id}
  useEffect(() => {
    if (!loggedIn) return;
    const t = setInterval(refresh, 5000);
    return () => clearInterval(t);
  }, [loggedIn]);

  async function handleLogin() {
    try {
      // auto-register fallback for demo
      try { await apiLogin(email, password); }
      catch {
        const reg = await fetch("http://localhost:8000/api/v1/auth/register", {
          method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ email, password }),
        });
        const d = await reg.json();
        localStorage.setItem("sentinel_token", d.access_token);
      }
      setLoggedIn(true);
    } catch (e: any) { setMsg(String(e.message)); }
  }

  async function submitTask() {
    setMsg("Submitting…");
    const res = await api("/api/v1/executions", {
      method: "POST",
      body: JSON.stringify({ objective, mode, max_steps: Number(maxSteps), max_cost: Number(maxCost) }),
    });
    setMsg(`Execution ${res.id} → ${res.status}`);
    refresh();
  }

  async function viewTrace(id: string) { setTrace(await api(`/api/v1/executions/${id}/trace`)); }

  if (!loggedIn) {
    return (
      <main className="min-h-screen flex items-center justify-center p-6">
        <div className="panel p-8 max-w-sm w-full">
          <h1 className="text-2xl font-bold mb-1">SENTINEL</h1>
          <p className="text-zinc-400 mb-6 text-sm">Autonomy with accountability. Every action bounded, observable, recoverable.</p>
          <input className="input mb-3" value={email} onChange={e => setEmail(e.target.value)} placeholder="email" />
          <input className="input mb-4" type="password" value={password} onChange={e => setPassword(e.target.value)} placeholder="password" />
          <button className="btn w-full" onClick={handleLogin}>Login / Register</button>
          {msg && <p className="text-red-400 mt-3 text-sm">{msg}</p>}
        </div>
      </main>
    );
  }

  const chartData = [{ name: "Executions", total: overview?.total || 0, ok: overview?.successful || 0, fail: overview?.failed || 0 }];

  return (
    <main className="min-h-screen p-6 max-w-7xl mx-auto">
      <header className="flex justify-between items-center mb-6">
        <h1 className="text-2xl font-bold">SENTINEL <span className="text-zinc-500 text-sm font-normal">Agentic Workflow Engine</span></h1>
        <span className="mono text-xs text-zinc-400">dark graphite · violet/blue · mono telemetry</span>
      </header>

      <section className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
        {[["Total Executions", overview?.total ?? "—"], ["Successful", overview?.successful ?? "—"],
          ["Failed", overview?.failed ?? "—"], ["Spend ($)", overview?.total_spend ?? "—"],
          ["Tokens", overview?.total_tokens ?? "—"], ["Success Rate", overview ? `${Math.round(overview.success_rate * 100)}%` : "—"],
          ["Data", overview?.data_source ?? ""]].map(([k, v]: any) => (
          <div key={k} className="panel p-4"><p className="text-zinc-400 text-xs">{k}</p><p className="text-xl font-bold">{v}</p></div>
        ))}
      </section>

      <BarChart width={500} height={140} data={chartData}>
        <Bar dataKey="total" fill="#7c6cff" /><Bar dataKey="ok" fill="#3b9eff" /><Bar dataKey="fail" fill="#ef4444" />
        <XAxis dataKey="name" stroke="#888" /><YAxis stroke="#888" /><Tooltip />
      </BarChart>

      <section className="panel p-6 mb-6">
        <h2 className="font-bold mb-3">Task Console</h2>
        <textarea className="input mb-3" rows={3} value={objective} onChange={e => setObjective(e.target.value)} />
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-4">
          <select className="input" value={mode} onChange={e => setMode(e.target.value)}>
            <option value="manual">Manual</option><option value="supervised">Supervised</option><option value="autonomous">Autonomous</option>
          </select>
          <input className="input" type="number" value={maxSteps} onChange={e => setMaxSteps(Number(e.target.value))} placeholder="max steps" />
          <input className="input" type="number" step="0.01" value={maxCost} onChange={e => setMaxCost(Number(e.target.value))} placeholder="max cost" />
          <button className="btn" onClick={submitTask}>Execute</button>
        </div>
        {msg && <p className="mono text-xs text-emerald-300">{msg}</p>}
      </section>

      <div className="grid md:grid-cols-2 gap-6">
        <section className="panel p-6">
          <h2 className="font-bold mb-3">Execution History</h2>
          {execs.map(e => (
            <div key={e.id} className="flex justify-between py-2 border-b border-zinc-800 text-sm">
              <span className="mono">{e.id.slice(0, 8)} · {e.status}</span>
              <span className="text-zinc-400">{e.objective.slice(0, 40)}…</span>
              <button className="text-violet-300 underline" onClick={() => viewTrace(e.id)}>Trace</button>
            </div>
          ))}
        </section>
        <section className="panel p-6">
          <h2 className="font-bold mb-3">Approvals</h2>
          {approvals.length === 0 && <p className="text-zinc-500 text-sm">No approvals yet.</p>}
          {approvals.map(a => (
            <div key={a.id} className="py-2 border-b border-zinc-800 text-sm flex justify-between">
              <span>{a.tool_id} · {a.risk_level} · {a.status}</span>
              <span>
                <button className="text-emerald-300 underline mr-2" onClick={async () => { await api(`/api/v1/approvals/${a.id}/approve`, { method: "POST", body: JSON.stringify({ decision: "approve" }) }); refresh(); }}>Approve</button>
                <button className="text-red-300 underline" onClick={async () => { await api(`/api/v1/approvals/${a.id}/reject`, { method: "POST", body: JSON.stringify({ decision: "reject" }) }); refresh(); }}>Reject</button>
              </span>
            </div>
          ))}
          <h2 className="font-bold mt-6 mb-3">Tools</h2>
          {tools.map(t => (
            <div key={t.tool_id} className="flex justify-between py-1 text-sm">
              <span className="mono">{t.tool_id}</span><span className="text-zinc-400">{t.risk_level} · {t.enabled ? "enabled" : "disabled"}</span>
            </div>
          ))}
        </section>
      </div>

      {trace && (
        <section className="panel p-6 mt-6">
          <h2 className="font-bold mb-3">Live Trace (React Flow data)</h2>
          <pre className="mono text-xs overflow-auto max-h-80">{JSON.stringify(trace, null, 2)}</pre>
          <p className="text-zinc-500 text-xs mt-2">Node states: pending/running/completed/failed/waiting_approval/skipped — render with React Flow in prod.</p>
        </section>
      )}
    </main>
  );
}
