"use client";
import { useState } from "react";
import { api } from "@/lib/api";

const PROVIDERS: Record<string, { label: string; hint: string; url: string; modelExample: string }> = {
  openai: { label: "OpenAI", hint: "Key starts with sk-… Get it at platform.openai.com/api-keys", url: "https://platform.openai.com/api-keys", modelExample: "gpt-4o-mini" },
  groq: { label: "Groq (free tier)", hint: "Key starts with gsk_… Get it at console.groq.com", url: "https://console.groq.com/keys", modelExample: "openai/gpt-oss-20b" },
  anthropic: { label: "Anthropic", hint: "Key starts with sk-ant-… Get it at console.anthropic.com", url: "https://console.anthropic.com/settings/keys", modelExample: "claude-3-5-sonnet" },
  google: { label: "Google Gemini", hint: "Gemini API key from Google AI Studio", url: "https://aistudio.google.com/apikey", modelExample: "gemini-1.5-flash" },
};

export default function ApiKeyPanel({ credentials, onSaved, onUseProvider }: {
  credentials: any[]; onSaved: () => void; onUseProvider?: (p: string, m: string) => void;
}) {
  const [provider, setProvider] = useState("openai");
  const [apiKey, setApiKey] = useState("");
  const [baseUrl, setBaseUrl] = useState("");
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState("");
  const [ok, setOk] = useState("");

  const info = PROVIDERS[provider];

  async function save() {
    if (!apiKey.trim()) { setErr("Paste your API key first."); return; }
    setBusy(true); setErr(""); setOk("");
    try {
      await api("/api/v1/auth/credentials", {
        method: "POST",
        body: JSON.stringify({ provider, api_key: apiKey.trim(), base_url: baseUrl.trim(), is_default: true }),
      });
      setApiKey(""); setOk(`${info.label} key saved (encrypted). Now pick ${info.label} in the Task Console and run.`);
      onSaved();
      onUseProvider?.(provider, info.modelExample);
    } catch (e: any) { setErr(String(e.message || e)); }
    setBusy(false);
  }

  return (
    <section className="panel p-6 mb-6 border-violet-500/40" id="api-keys">
      <h2 className="font-bold text-lg mb-1">🔑 Add your AI API key</h2>
      <p className="text-zinc-400 text-sm mb-4">
        SENTINEL runs free on the built-in mock LLM. Add a real key (OpenAI, Groq, Anthropic, Gemini) to use real models.
        Keys are encrypted and <b>never shown again</b> — you can skip this and use the mock.
      </p>
      <div className="grid grid-cols-2 md:grid-cols-4 gap-2 mb-3">
        {Object.entries(PROVIDERS).map(([id, p]) => (
          <button key={id} onClick={() => setProvider(id)}
            className={`p-3 rounded-xl border text-left ${provider === id ? "border-violet-400 bg-violet-500/10" : "border-zinc-700 hover:border-zinc-500"}`}>
            <span className="font-semibold text-sm">{p.label}</span>
            <span className="block text-xs text-zinc-500 mt-1">{p.modelExample}</span>
          </button>
        ))}
      </div>
      <p className="text-xs text-zinc-400 mb-3">{info.hint} · <a className="underline text-violet-300" href={info.url} target="_blank" rel="noreferrer">Get a key →</a></p>
      <div className="grid md:grid-cols-[1fr_auto] gap-3 mb-3">
        <input className="input" type="password" value={apiKey} onChange={e => setApiKey(e.target.value)}
          placeholder={`${info.label} API key`} autoComplete="off" />
        <button className="btn" onClick={save} disabled={busy}>{busy ? "Saving…" : "Save key"}</button>
      </div>
      <input className="input mb-3" value={baseUrl} onChange={e => setBaseUrl(e.target.value)} placeholder="Base URL (optional — leave empty for default)" />
      {err && <p className="text-red-400 text-sm mb-2">{err}</p>}
      {ok && <p className="text-emerald-300 text-sm mb-2">{ok}</p>}
      <div>
        {credentials.map((c: any) => (
          <p key={c.provider} className="mono text-xs text-zinc-400 py-1">
            ✅ {c.provider} {c.is_default ? "(default)" : ""} · {c.key_hint} {c.base_url ? `· ${c.base_url}` : ""}
          </p>
        ))}
        {credentials.length === 0 && <p className="text-zinc-500 text-sm">No keys saved — using free mock LLM.</p>}
      </div>
    </section>
  );
}
