const BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export function getToken(): string {
  if (typeof window === "undefined") return "";
  return localStorage.getItem("sentinel_token") || "";
}

export async function api(path: string, opts: RequestInit = {}) {
  const headers: Record<string, string> = { "Content-Type": "application/json", ...(opts.headers as any || {}) };
  const token = getToken();
  if (token) headers["Authorization"] = `Bearer ${token}`;
  const res = await fetch(`${BASE}${path}`, { ...opts, headers });
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

export async function login(email: string, password: string) {
  const res = await fetch(`${BASE}/api/v1/auth/login`, {
    method: "POST", headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, password }),
  });
  if (!res.ok) throw new Error(await res.text());
  const data = await res.json();
  localStorage.setItem("sentinel_token", data.access_token);
  return data;
}
