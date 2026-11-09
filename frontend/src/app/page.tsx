"use client";
import { useEffect, useState } from "react";
import Link from "next/link";
import { api, login as apiLogin, getToken } from "@/lib/api";
import ApiKeyPanel from "@/components/ApiKeyPanel";
import { BarChart, Bar, XAxis, YAxis, Tooltip } from "recharts";

type Exec = { id: string; objective: string; status: string; total_cost: number; total_tokens: number };
type Tool = { tool_id: string; name: string; description: string; risk_level: string; enabled: boolean };
type Approval = { id: string; execution_id: string; tool_id: string; risk_level: string; status: string };

const EXAMPLES = [
  "Research the latest developments in agentic AI, compare five frameworks, summarize their advantages",
  "What are the advantages of agentic AI? Summarize in 3 bullets.",
  "Calculate 42 * 17 and show the steps",
  "Write a report file called summary.md with a short intro",
];

const PROVIDER_MODELS: Record<string, string> = {
  mock: "mock-llm-1", openai: "gpt-4o-mini", groq: "llama-3.1-8b-instant",
  anthropic: "claude-3-5-sonnet", google: "gemini-1.5-flash",
};

const STATUS_STYLE: Record<string, string> = {
  completed: "text-emerald-300", failed: "text-red-300", running: "text-blue-300",
  awaiting_approval: "text-amber-300", budget_exceeded: "text-amber-300",
  limit_exceeded: "text-amber-300", cancelled: "text-zinc-400", queued: "text-zinc-300",
};

export default function Page() {
  const [email, setEmail] = useState("demo@example.com");
  const [password, setPassword] = useState("password123");
  const [loggedIn, setLoggedIn] = useState(false);
  const [objective, setObjective] = useState(EXAMPLES[0]);
  const [mode, setMode] = useState("supervised");
  const [maxSteps, setMaxSteps] = useState(20);
  const [maxCost, setMaxCost] = useState(1.0);
  const [provider, setProvider] = useState("mock");
  const [model, setModel] = useState("mock-llm-1");
  const [credentials, setCredentials] = useState<any[]>([]);
  const [overview, setOverview] = useState<any>(null);
  const [execs, setExecs] = useState<Exec[]>([]);
  const [tools, setTools] = useState<Tool[]>([]);
  const [approvals, setApprovals] = useState<Approval[]>([]);
  const [trace, setTrace] = useState<any>(null);
  const [msg, setMsg] = useState("");
  const [busy, setBusy] = useState(false);

  async function refresh() {
    if (!getToken()) return;
    try {
      setOverview(await api("/api/v1/analytics/overview"));
      setExecs(await api("/api/v1/executions"));
      setTools(await api("/api/v1/tools"));
      setApprovals(await api("/api/v1/approvals"));
      setCredentials(await api("/api/v1/auth/credentials"));
    } catch (e: any) { setMsg(String(e.message || e)); }
  }

  useEffect(() => { if (getToken()) { setLoggedIn(true); refresh(); } }, []);
  useEffect(() => { if (!loggedIn) return; const t = setInterval(refresh, 5000); return () => clearInterval(t); }, [loggedIn]);

  async function handleLogin() {
    setBusy(true); setMsg("");
    try {
      try { await apiLogin(email, password); }
      catch {
        const reg = await fetch("http://localhost:8000/api/v1/auth/register", {
          method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ email, password }),
        });
        const d = await reg.json();
        if (!d.access_token) throw new Error("Login failed — check email/password");
        localStorage.setItem("sentinel_token", d.access_token);
      }
      setLoggedIn(true); setMsg("Welcome! Tell SENTINEL what to do below.");
    } catch (e: any) { setMsg(`😕 ${String(e.message || e)}`); }
    setBusy(false);
  }

  async function submitTask() {
    if (!objective.trim()) { setMsg("Please type what you want SENTINEL to do first."); return; }
    setBusy(true); setMsg("⏳ Planning + running…");
    try {
      const res = await api("/api/v1/executions", {
        method: "POST",
        body: JSON.stringify({ objective, mode, max_steps: Number(maxSteps), max_cost: Number(maxCost), provider, model }),
      });
      const hints: Record<string, string> = {
        completed: "✅ Done — see Trace below for details.", awaiting_approval: "⏸ Waiting for your approval in Approval Center.",
        budget_exceeded: "💰 Budget exceeded — increase max cost or remove paid tools.", limit_exceeded: "🛑 Step limit hit — increase max steps to allow longer plans.",
        failed: `❌ Failed: ${res.error || "see Trace"}`, cancelled: "Cancelled.", running: "Running…",
      };
      setMsg(hints[res.status] || `Execution ${res.id} → ${res.status}`);
      refresh();
    } catch (e: any) { setMsg(`😕 ${String(e.message || e)}`); }
    setBusy(false);
  }

  async function viewTrace(id: string) { setTrace(await api(`/api/v1/executions/${id}/trace`)); }

  function pickProvider(p: string, m?: string) {
    setProvider(p); setModel(m || PROVIDER_MODELS[p] || "");
    setMsg(p === "mock" ? "Using free mock LLM (offline)." : `Using ${p} with model ${m || PROVIDER_MODELS[p]}.`);
  }

  if (!loggedIn) {
    return (
      <main className="min-h-screen flex items-center justify-center p-6">
        <div className="panel p-8 max-w-md w-full">
          <h1 className="text-3xl font-bold mb-1">🛡️ SENTINEL</h1>
          <p className="text-zinc-400 mb-2"><b>Autonomy with accountability.</b> Give it a goal — it plans, runs tools safely, watches your budget, and asks before anything risky.</p>
          <ol className="text-sm text-zinc-400 mb-6 list-decimal ml-5 space-y-1">
            <li>Log in (or create a free account)</li>
            <li>Optionally add an AI key (or use the free mock)</li>
            <li>Type a goal and run it — <Link href="/tutorial" className="underline text-violet-300">2-min tutorial →</Link></li>
          </ol>
          <label className="text-xs text-zinc-500">EMAIL</label>
          <input className="input mb-3" value={email} onChange={e => setEmail(e.target.value)} placeholder="you@example.com" />
          <label className="text-xs text-zinc-500">PASSWORD (8+ characters)</label>
          <input className="input mb-4" type="password" value={password} onChange={e => setPassword(e.target.value)} placeholder="••••••••" />
          <button className="btn w-full" onClick={handleLogin} disabled={busy}>{busy ? "Please wait…" : "Login / Create account"}</button>
          {msg && <p className="text-red-400 mt-3 text-sm">{msg}</p>}
          <p className="text-zinc-600 text-xs mt-4">Demo account: demo@example.com / password123 · No email verification.</p>
        </div>
      </main>
    );
  }

  const chartData = overview ? [{ name: "Runs", total: overview.total, ok: overview.successful, fail: overview.failed }] : [];
  const pending = approvals.filter(a => a.status === "pending");

  return (
    <main className="max-w-7xl mx-auto p-4 md:p-6">
      <div className="flex flex-wrap justify-between items-center gap-3 mb-6">
        <div>
          <h1 className="text-2xl font-bold">What do you want SENTINEL to do?</h1>
          <p className="text-zinc-400 text-sm">Type a goal in plain English. It plans, runs tools, tracks cost, and asks before risky steps.</p>
        </div>
        <Link href="/tutorial" className="text-sm underline text-violet-300">📖 New here? 2-min tutorial →</Link>
      </div>

      <section className="panel p-6 mb-6">
        <h2 className="font-bold mb-3">🚀 Task Console</h2>
        <textarea className="input mb-3" rows={3} value={objective} onChange={e => setObjective(e.target.value)}
          placeholder="e.g. Research agentic AI, compare 5 frameworks, summarize advantages…" />
        <div className="flex flex-wrap gap-2 mb-4">
          {EXAMPLES.map(ex => (
            <button key={ex} onClick={() => setObjective(ex)}
              className="text-xs border border-zinc-700 rounded-full px-3 py-1.5 hover:border-violet-400 hover:text-violet-300">{ex.slice(0, 42)}…</button>
          ))}
        </div>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-3">
          <div>
            <label className="text-xs text-zinc-500">HOW CAREFULLY?</label>
            <select className="input" value={mode} onChange={e => setMode(e.target.value)}>
              <option value="manual">🖐 Manual — I approve everything</option>
              <option value="supervised">👀 Supervised — approve risky only (recommended)</option>
              <option value="autonomous">🤖 Autonomous — run within my limits</option>
            </select>
          </div>
          <div>
            <label className="text-xs text-zinc-500">MODEL</label>
            <select className="input" value={provider} onChange={e => pickProvider(e.target.value)}>
              <option value="mock">mock — free, offline</option><option value="openai">OpenAI</option>
              <option value="groq">Groq (free tier)</option><option value="anthropic">Anthropic</option><option value="google">Google Gemini</option>
            </select>
          </div>
          <div>
            <label className="text-xs text-zinc-500">MODEL NAME</label>
            <input className="input" value={model} onChange={e => setModel(e.target.value)} placeholder="gpt-4o-mini" />
          </div>
          <div>
            <label className="text-xs text-zinc-500">MAX COST ($)</label>
            <input className="input" type="number" step="0.01" min="0.01" value={maxCost} onChange={e => setMaxCost(Number(e.target.value))} />
          </div>
        </div>
        <div className="flex items-center gap-3 mb-3 text-xs text-zinc-500">
          <label>Max steps <input className="input inline-block w-20 ml-1" type="number" value={maxSteps} onChange={e => setMaxSteps(Number(e.target.value))} /></label>
          <span>Guardrails stop the run safely if you hit a limit — nothing runs away.</span>
        </div>
        <button className="btn" onClick={submitTask} disabled={busy}>{busy ? "Running…" : "▶ Run task"}</button>
        {msg && <p className="text-sm mt-3 text-zinc-200">{msg}</p>}
      </section>

      <ApiKeyPanel credentials={credentials} onSaved={refresh} onUseProvider={pickProvider} />

      {pending.length > 0 && (
        <section className="panel p-6 mb-6 border-amber-400/50">
          <h2 className="font-bold mb-2">⏸ {pending.length} approval{pending.length > 1 ? "s" : ""} waiting for you</h2>
          {pending.map(a => (
            <div key={a.id} className="flex flex-wrap justify-between gap-2 py-2 border-b border-zinc-800 text-sm">
              <span><b>{a.tool_id}</b> · risk {a.risk_level} · run {a.execution_id.slice(0, 8)}</span>
              <span>
                <button className="text-emerald-300 underline mr-3" onClick={async () => { await api(`/api/v1/approvals/${a.id}/approve`, { method: "POST", body: JSON.stringify({ decision: "approve" }) }); setMsg("✅ Approved — resume the run from History."); refresh(); }}>Approve</button>
                <button className="text-red-300 underline" onClick={async () => { await api(`/api/v1/approvals/${a.id}/reject`, { method: "POST", body: JSON.stringify({ decision: "reject" }) }); refresh(); }}>Reject</button>
              </span>
            </div>
          ))}
        </section>
      )}

      <section className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
        {[["Total runs", overview?.total ?? "—"], ["✅ Succeeded", overview?.successful ?? "—"],
          ["❌ Failed", overview?.failed ?? "—"], ["💰 Spent", overview ? `$${overview.total_spend}` : "—"],
          ["🎟 Tokens", overview?.total_tokens ?? "—"], ["📈 Success rate", overview ? `${Math.round(overview.success_rate * 100)}%` : "—"]].map(([k, v]: any) => (
          <div key={k} className="panel p-4"><p className="text-zinc-400 text-xs">{k}</p><p className="text-xl font-bold">{v}</p></div>
        ))}
      </section>

      {chartData.length > 0 && (
        <div className="panel p-4 mb-6 inline-block">
          <BarChart width={520} height={150} data={chartData}>
            <Bar dataKey="total" fill="#7c6cff" name="Total" /><Bar dataKey="ok" fill="#3b9eff" name="OK" /><Bar dataKey="fail" fill="#ef4444" name="Failed" />
            <XAxis dataKey="name" stroke="#888" /><YAxis stroke="#888" /><Tooltip />
          </BarChart>
        </div>
      )}

      <div className="grid md:grid-cols-2 gap-6">
        <section className="panel p-6">
          <h2 className="font-bold mb-3">🕘 Your runs</h2>
          {execs.length === 0 && <p className="text-zinc-500 text-sm">No runs yet — run your first task above! 🎉</p>}
          {execs.map(e => (
            <div key={e.id} className="flex flex-wrap justify-between gap-2 py-2 border-b border-zinc-800 text-sm">
              <span className={`mono font-semibold ${STATUS_STYLE[e.status] || ""}`}>{e.status}</span>
              <span className="text-zinc-300 flex-1 text-center">{e.objective.slice(0, 44)}…</span>
              <button className="text-violet-300 underline" onClick={() => viewTrace(e.id)}>Trace</button>
            </div>
          ))}
        </section>
        <section className="panel p-6">
          <h2 className="font-bold mb-3">🧰 Tools ({tools.filter(t => t.enabled).length} available)</h2>
          {tools.map(t => (
            <div key={t.tool_id} className="flex justify-between py-1 text-sm">
              <span className="mono">{t.tool_id}</span>
              <span className="text-zinc-400 text-xs">{t.risk_level} · {t.enabled ? "✅" : "❌"}</span>
            </div>
          ))}
          <p className="text-zinc-600 text-xs mt-3">Risk guide: LOW auto-runs · MEDIUM may ask · HIGH/CRITICAL always ask (in supervised/manual).</p>
        </section>
      </div>

      {trace && (
        <section className="panel p-6 mt-6">
          <h2 className="font-bold mb-3">🔍 Trace — what exactly happened</h2>
          <pre className="mono text-xs overflow-auto max-h-80">{JSON.stringify(trace, null, 2)}</pre>
        </section>
      )}

      <footer className="text-center text-zinc-600 text-xs mt-10 pb-6">
        SENTINEL · Autonomy with accountability · <Link href="/tutorial" className="underline">Tutorial</Link> · <a href="http://localhost:8000/docs" target="_blank" rel="noreferrer" className="underline">API Docs</a>
      </footer>
    </main>
  );
}
