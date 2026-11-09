# SENTINEL — Architecture

```
USER → Next.js Dashboard →(REST/WS)→ FastAPI Gateway → Task Validation
  → Agent Planner (LLM→Pydantic Plan) → Plan Validation (Guardrails)
  → Cost Estimator / Budget Reserve → LangGraph Execution Engine
    ├─ ToolRegistry → GuardrailEngine → CostTracker → StateManager( PG+Redis)
    ├─ RecoveryManager (retry/checkpoint)  ├─ ApprovalManager (HITL)
    └─ Observability (logs/LangSmith/metrics)
  → Result Generator → Audit Log → Dashboard
```

## Components & Interfaces
| Component | Responsibility | Key Interface |
|---|---|---|
| API Gateway | auth, validation, rate-limit, WS | `api/v1/*` routers |
| TaskManager | create/list/cancel/resume executions | `services/task_service.py` |
| Planner | objective→DAG plan + estimates | `agents/planner.py: Planner.plan()` |
| Executor/Graph | LangGraph nodes + conditional edges | `workflows/execution_graph.py: build_graph()` |
| ToolRegistry | register/validate/invoke tools | `tools/registry.py: invoke()` |
| Guardrails | limits, permissions, risk, injection | `guardrails/{limits,permissions,validator}.py` |
| Cost Engine | pricing, tracking, budgets | `cost/{pricing,tracker,budget}.py` |
| StateManager | PG checkpoints + Redis hot state | `services/state_manager.py` |
| Recovery | backoff, resume, partial results | `recovery/manager.py` |
| Approvals | create/expire/approve binding to exact action hash | `approvals/manager.py` |
| Observability | correlation IDs, structured logs, traces | `observability/` |

## Execution Flow (LangGraph nodes)
`initialize → analyze → generate_plan → validate_plan → estimate_budget → [request_approval] → select_next_step → validate_tool_call → execute_tool → validate_output → update_cost → update_state → [detect_failure → recover] → finalize`
Edges: invalid plan→replan(≤3)/terminate; budget exceeded→terminate; approval→interrupt/resume; tool fail→recover; deps incomplete→wait; all done→finalize.

## Deployment
`docker compose`: postgres:16, redis:7, backend (uvicorn), worker (arq/celery-style asyncio worker entrypoint `app.worker`), frontend (Next standalone), nginx reverse proxy. Health: `/health`, `/health/ready` (DB+Redis).
