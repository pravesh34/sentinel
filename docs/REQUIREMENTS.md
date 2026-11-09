# SENTINEL — Requirements

## Functional
- Submit NL objective → structured plan (DAG) → validated → executed via LangGraph → audited result.
- 10 tools via central ToolRegistry only; no arbitrary code/shell.
- Hard limits (deterministic, outside LLM): 20 steps, 30 tool calls, 5 retries, 5 min, 3 concurrent, 3 replans, token & $ budgets — all configurable per execution.
- Risk: LOW/MEDIUM/HIGH/CRITICAL. HIGH/CRITICAL require HITL approval (Supervised/Manual modes; Autonomous never overrides CRITICAL).
- Cost: per-call/per-step/per-run/per-user/per-provider/model; estimated vs confirmed; pricing table versioned, not hardcoded in logic; reservation before paid calls; 75/90/100% warnings.
- Recovery: exponential backoff, Retry-After, provider fallback, checkpoint resume, idempotency keys, partial results. No infinite retry, no repeat of irreversible actions.
- Observability: correlation_id everywhere, structured logs (no secrets), LangSmith optional, trace API per execution.
- Frontend: Overview, Task Console, Live Execution (React Flow), Cost, History/Replay/Export, Approvals, Tools.
- Auth: register/login/me, JWT; per-user API credentials encrypted at rest (Fernet), never logged.

## Non-Functional
- Async FastAPI + SQLAlchemy2 + PostgreSQL (prod) / SQLite (dev/test fallback), Redis (prod) / in-memory fallback.
- Docker Compose: `docker compose up --build` (postgres, redis, backend, worker, frontend, nginx).
- Security: allow/deny tool policies, input schema validation (Pydantic), injection heuristic + sanitization, sandbox timeouts, rate limiting.
- Testing: unit/integration/security/E2E with mocked LLMs; CI must not need live API keys.

## Acceptance Demos
1 Normal multi-step, 2 Step limit (3), 3 Cost limit, 4 Unauthorized tool rejected, 5 HITL pause/resume, 6 Tool timeout → bounded retry, 7 Trace inspection, 8 Worker restart → checkpoint resume without duplicate irreversible actions.
