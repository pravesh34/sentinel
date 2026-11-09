"use client";
import Link from "next/link";

const Step = ({ n, title, body }: { n: string; title: string; body: React.ReactNode }) => (
  <section className="panel p-6 mb-4">
    <h3 className="font-bold text-lg mb-2"><span className="text-violet-300">Step {n}.</span> {title}</h3>
    <div className="text-zinc-300 text-sm space-y-2">{body}</div>
  </section>
);

const Code = ({ children }: { children: string }) => (
  <pre className="mono text-xs bg-black/40 rounded-lg p-3 overflow-auto text-emerald-200">{children}</pre>
);

export default function TutorialPage() {
  return (
    <main className="max-w-3xl mx-auto p-4 md:p-6">
      <h1 className="text-2xl font-bold mb-1">Tutorial — your first SENTINEL run in 2 minutes</h1>
      <p className="text-zinc-400 mb-6">No coding needed. You&apos;ll log in, (optionally) add an AI key, run a task, approve a risky action, and read the audit trail.</p>

      <Step n="1" title="Log in (or create an account)" body={<>
        <p>On the Dashboard, enter any email + password (8+ chars) and click <b>Login / Register</b>. Demo: <span className="mono">demo@example.com / password123</span>.</p>
        <p className="text-zinc-500">Your token is saved in your browser. No email verification needed.</p>
      </>} />

      <Step n="2" title="Add your AI API key (optional — free mock works)" body={<>
        <p>Scroll to <b>🔑 Add your AI API key</b>. Pick a provider, paste the key, click <b>Save key</b>.</p>
        <ul className="list-disc ml-5">
          <li><b>OpenAI</b> — <span className="mono">sk-…</span>, model <span className="mono">gpt-4o-mini</span></li>
          <li><b>Groq</b> — <span className="mono">gsk_…</span>, free tier, model <span className="mono">llama-3.1-8b-instant</span> (easiest to start)</li>
          <li><b>Anthropic</b> — <span className="mono">sk-ant-…</span> · <b>Google Gemini</b> — AI Studio key</li>
        </ul>
        <p className="text-zinc-500">Keys are encrypted, never displayed again, and only used for your runs. Each card links to “Get a key”. Skip this step to use the free mock LLM.</p>
      </>} />

      <Step n="3" title="Run your first task" body={<>
        <p>In <b>Task Console</b>, type a goal (or tap an example chip), choose a mode, and click <b>▶ Run task</b>.</p>
        <p><b>Recommended first run:</b> <span className="mono">What are the advantages of agentic AI? Summarize.</span> with Supervised + mock.</p>
        <ul className="list-disc ml-5">
          <li><b>Manual</b> — approve every tool call (safest).</li>
          <li><b>Supervised</b> — auto-run safe tools, approve risky ones (default, recommended).</li>
          <li><b>Autonomous</b> — run within your limits; critical actions still ask you.</li>
        </ul>
      </>} />

      <Step n="4" title="Approve a risky action (human-in-the-loop)" body={<>
        <p>Ask for something risky — e.g. <span className="mono">Write a report file called summary.md</span>. The run pauses with <b>awaiting approval</b>.</p>
        <p>Open <b>Approval Center</b> → review tool + arguments + risk level → <b>Approve</b> or <b>Reject</b>. Approval applies to <i>exactly</i> those arguments and expires in 10 minutes.</p>
      </>} />

      <Step n="5" title="Read the trace & cost" body={<>
        <p>Click <b>Trace</b> on any run in Execution History. You&apos;ll see every step, tool call, token usage, cost, and audit event — with a correlation ID you can search in logs.</p>
        <p>The cards at the top show total runs, success rate, spend, and tokens. The API Docs page (<a className="underline" href="http://localhost:8000/docs" target="_blank" rel="noreferrer">localhost:8000/docs</a>) has the same data for scripts.</p>
      </>} />

      <Step n="6" title="Try the 4 guardrail demos" body={<>
        <table className="w-full text-sm">
          <thead><tr className="text-zinc-500"><th className="text-left py-1">Demo</th><th className="text-left py-1">Settings</th><th className="text-left py-1">Result</th></tr></thead>
          <tbody>
            <tr className="border-t border-zinc-800"><td className="py-1">Step limit</td><td className="mono text-xs">max_steps=1</td><td>limit_exceeded</td></tr>
            <tr className="border-t border-zinc-800"><td className="py-1">Cost limit</td><td className="mono text-xs">max_cost=0.0001</td><td>budget_exceeded</td></tr>
            <tr className="border-t border-zinc-800"><td className="py-1">Unauthorized tool</td><td className="mono text-xs">allowed_tools=calc only</td><td>guardrail rejects</td></tr>
            <tr className="border-t border-zinc-800"><td className="py-1">Failure recovery</td><td className="mono text-xs">slow/hard tool</td><td>bounded retries + partial result</td></tr>
          </tbody>
        </table>
      </>} />

      <Step n="7" title="Script it with curl (optional)" body={<>
        <Code>{`TOKEN=$(curl -s -X POST http://localhost:8000/api/v1/auth/login \\
  -H 'Content-Type: application/json' \\
  -d '{"email":"you@example.com","password":"password123"}' | python3 -c 'import sys,json;print(json.load(sys.stdin)["access_token"])')

curl -X POST http://localhost:8000/api/v1/executions \\
  -H "Authorization: Bearer $TOKEN" -H 'Content-Type: application/json' \\
  -d '{"objective":"Summarize agentic AI in 3 bullets","provider":"openai","model":"gpt-4o-mini"}'`}</Code>
      </>} />

      <div className="panel p-6 text-center">
        <p className="mb-3">Ready?</p>
        <Link href="/" className="btn">Go to Dashboard →</Link>
        <p className="text-zinc-500 text-xs mt-3">Stuck? Check API Docs, backend logs (`docker compose logs -f backend`), and /health on :8000.</p>
      </div>
    </main>
  );
}
