# SENTINEL — Security

**Trust model:** LLM is untrusted. All enforcement is deterministic Python outside prompts.

- **Tool isolation:** agents can only call ToolRegistry.invoke(); no arbitrary functions/shell; Python sandbox blocks os/sys/subprocess/socket/dunders.
- **Validation:** Pydantic schemas for API + tool input schemas; unknown tools rejected; allowlist per execution (`allowed_tools`).
- **Risk/HITL:** HIGH/CRITICAL need approval bound to exact `action_hash(execution,step,tool,args)` — cannot reuse for modified args; expires 10 min; CRITICAL always requires approval even in autonomous mode.
- **Limits:** steps/tool-calls/retries/runtime/tokens/$ enforced in `guardrails/limits.py` before every step; violations → status budget_exceeded/limit_exceeded + partial result.
- **Secrets:** API keys Fernet-encrypted at rest, never logged/returned; structured logs scrubbed (no keys/passwords); correlation IDs for audit.
- **Injection:** system/untrusted separation, tool-output sanitization (control-char strip, 8k cap), injection-pattern warning logged; retrieved content never auto-trusted.
- **Budgets/concurrency:** reservation before paid ops; DB cost aggregates prevent bypass; idempotency keys prevent duplicate irreversible actions.
- **Threats mitigated:** prompt injection, tool-chain privilege escalation, unauthorized tool use, budget exhaustion, replay of approvals, secret leakage, sandbox escape (basic), SSRF (https-only for http_request).
- **Residual:** malicious tool impls, provider compromise, DB breach — mitigate with least-privilege DB roles, per-tool network policy, audit review in prod.
