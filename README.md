# SENTINEL — Production-Grade Agentic Workflow Engine

**Autonomy with accountability. Every action must be bounded, observable, and recoverable.**

SENTINEL turns a natural-language objective into a validated, budgeted, approval-gated execution plan, runs it via LangGraph through a central Tool Registry with hard deterministic guardrails, tracks every token/dollar, checkpoints state, recovers from failures, and produces a full audit trail — all visible in a live dashboard.

```text
USER → Next.js → FastAPI → Planner → Plan Validation → LangGraph Engine
  → Tool Registry + Guardrails + Cost Tracker + State + Recovery + HITL
  → Result + Audit Log → Dashboard
```

## Quick Start

```bash
docker compose up --build
# Frontend: http://localhost:3000   API docs: http://localhost:8000/docs   nginx: http://localhost:8080
```

Local dev (no Docker):
```bash
cd backend && pip install -e ".[dev]" && python3 -m pytest tests -q && uvicorn app.main:app --reload
cd frontend && npm install && npm run dev
```

## How It Works

1. Submit objective in Task Console (mode: manual/supervised/autonomous).
2. **Planner** (mock by default) → Pydantic DAG plan; unknown tools rejected.
3. **Guardrails** validate plan vs hard limits (20 steps / 30 calls / 5 retries / 5 min / 3 concurrent / 3 replans / token & $ budgets).
4. **Executor** runs step-by-step: permission → schema → HITL approval (HIGH/CRITICAL) → budget reservation → tool invoke via registry → sanitize → checkpoint + audit.
5. **Cost** tracked per call/step/run/user/provider/model (pricing table versioned, estimated vs confirmed).
6. Failures → bounded retry (exponential backoff, Retry-After) → partial result; crashes → worker resumes from last checkpoint without duplicating irreversible actions (idempotency keys).
7. **Dashboard** shows live trace, cost analytics, approvals, tool health; `/trace` API exports full audit as JSON.

## Demo Scenarios (8 acceptance demos)

| Demo | How to run |
|---|---|
| 1 Normal | Submit "Research agentic AI…" → watch plan/tools/final report |
| 2 Step limit | Set max_steps=1, submit multi-step task → `limit_exceeded` |
| 3 Cost limit | max_cost=0.0001 → `budget_exceeded`, paid ops stopped |
| 4 Tool security | allowed_tools=["calculator"] + research task → guardrail rejects web_search, partial result |
| 5 HITL | Task needing file_writer/http (HIGH) in supervised → pauses `awaiting_approval` → approve via Approval Center → resume |
| 6 Failure recovery | Tool timeout → bounded retries logged in trace |
| 7 Observability | History → Trace → tokens/cost/latency/tool calls; export JSON |
| 8 State recovery | Kill worker mid-run → restart (`app.worker`) → resumes from checkpoint, no duplicate writes |

## Tech Stack

Python 3.12+ FastAPI Pydantic v2 SQLAlchemy 2 PostgreSQL Redis LangGraph LangChain LangSmith · Next.js TypeScript Tailwind shadcn-style Recharts React Flow WebSockets · Docker Compose Nginx GitHub Actions Pytest Ruff MyPy Alembic.

LLM providers (all behind `providers/base.py`): mock (default, offline), OpenAI, Google Gemini, Groq, Anthropic.

**Add an API key (2 ways):**
1. **Dashboard (recommended):** open http://localhost:3000 → "API Keys" panel → pick provider, paste key, Save Key. Pick provider + model in Task Console and Execute. Keys are Fernet-encrypted, never returned by any API.
2. **API/curl:**
   ```bash
   curl -X POST http://localhost:8000/api/v1/auth/credentials -H "Authorization: Bearer $TOKEN" \
     -H 'Content-Type: application/json' -d '{"provider":"openai","api_key":"sk-...","is_default":true}'
   curl -X POST http://localhost:8000/api/v1/executions -H "Authorization: Bearer $TOKEN" \
     -H 'Content-Type: application/json' -d '{"objective":"...","provider":"openai","model":"gpt-4o-mini"}'
   ```
   Server fallback: set `OPENAI_API_KEY` / `GROQ_API_KEY` / `ANTHROPIC_API_KEY` / `GEMINI_API_KEY`, `DEFAULT_PROVIDER`, `FALLBACK_PROVIDER` in `.env` (see `.env.example`).
   OpenAI/Groq use OpenAI-compatible endpoints; for Anthropic/Google native APIs set `base_url` on the credential. Real web search: swap `web_search` handler for SerpAPI/Tavily key (currently labeled mock offline).

## Project Structure

```
sentinel/
├── backend/app/{api/v1, agents/{planner,executor,state}, workflows/execution_graph,
│   guardrails/{limits,permissions,validator}, cost/{tracker,pricing,budget},
│   tools/{registry,implementations}, recovery, approvals, observability,
│   database, models, schemas, services, providers, main.py, worker.py}
├── backend/tests/ (39 tests)  backend/migrations/ (Alembic)
├── frontend/src/{app,components,features,hooks,services,types,lib}
├── infrastructure/{docker,nginx,monitoring}  docs/  scripts/
├── docker-compose.yml  .env.example  README.md
```

## Testing

```bash
cd backend && python3 -m pytest tests -q   # 39 passed, mocked LLM, no live keys
```

## Docs

`docs/REQUIREMENTS.md · DESIGN.md · ARCHITECTURE.md · DATABASE.md · IMPLEMENTATION_PLAN.md · API.md · SECURITY.md · TESTING.md · DEPLOYMENT.md`

## Architecture / DB / Flow Diagrams

```
Execution flow:  initialize → analyze → generate_plan → validate → estimate → [approval]
  → select_step → validate_tool → execute → validate_output → update_cost/state
  → [fail→recover] → finalize   (LangGraph StateGraph, checkpointed per node)

DB (PostgreSQL, UUID PK, JSONB): users, api_credentials(enc), executions, execution_steps,
execution_plans, tool_registry, tool_invocations(idempotency UNIQUE), cost_records,
budget_limits, execution_checkpoints, approval_requests(action_hash), audit_logs,
provider_pricing(versioned), execution_errors
```

## Security & Constraints

LLM never enforces its own limits; no arbitrary code/shell (sandbox blocks imports/dunders); budgets reserved before paid calls; approvals bound to exact args; secrets encrypted & never logged; mock data always labeled (`mock: true`).

## License

MIT — see `LICENSE`. Built as a senior-engineering portfolio / final-year project.
