# SENTINEL — Implementation Plan (Phases)

- **P1 Foundation**: repo, FastAPI+Pydantic v2, SQLAlchemy models+SQLite/PG, Redis/in-mem fallback, JWT auth, health. ✅ This build.
- **P2 Agent Engine**: LangGraph StateGraph, Planner (MockLLM+providers), 10 tools via registry, state/checkpoints. ✅
- **P3 Guardrails**: hard limits, tool validation, risk+HITL, injection heuristic, allow/deny. ✅
- **P4 Cost**: versioned pricing, tracker, reservation/reconciliation, budget enforcement + warnings. ✅
- **P5 Recovery/Obs**: backoff, fallback, resume, idempotency, structured logs, LangSmith optional, trace API. ✅
- **P6 Dashboard**: Next.js overview/console/live/cost/history/approvals/tools, WS+polling. ✅
- **P7 Testing/Deploy**: 20 scenarios (mocked LLM), Docker Compose, nginx, GitHub Actions. ✅ (run `pytest`)

## Run
```bash
cd backend && pip install -e ".[dev]" && pytest -q
docker compose up --build  # from sentinel/
# open http://localhost:3000  API docs http://localhost:8000/docs
```
## Demos
See README § Demo Scenarios (8 demos mapped to tests + curl).
