# SENTINEL — Design

## Philosophy
**Autonomy with accountability. Every action bounded, observable, recoverable.**

## Design Principles
1. LLM proposes, deterministic code disposes. Guardrails/limits/cost are pure Python, never prompt-based.
2. Registry pattern: tools/execution only via ToolRegistry.invoke() → Guardrail check → Cost reserve → handler → validation → audit.
3. State machine (LangGraph StateGraph): all transitions explicit, checkpointed to PostgreSQL + Redis.
4. Fail closed: unknown tool, invalid args, missing permission, exceeded budget ⇒ reject/terminate, preserve state, partial result.
5. Idempotency: `idempotency_key = sha256(execution_id:step_id:tool:args_hash)`; irreversible tools skip if already committed.
6. Separation: API routes thin → services → agents/workflows → tools. No logic in route handlers.

## Key Decisions
- **MockLLM default** for tests/offline; real providers behind abstraction (OpenAI/Gemini/Groq/Anthropic) with fallback chain. Clear `mock:` labelling — no fabricated prod analytics.
- **Sync SQLAlchemy** for portability (SQLite↔Postgres via DATABASE_URL) + async execution via asyncio tasks; Redis optional with in-memory fallback so `pytest` & local dev work without infra.
- **Risk defaults**: calculator/summarizer LOW; web_search/file_read/db_query MEDIUM; file_write/http_post HIGH; delete/finance/message CRITICAL.
- **Pricing**: `provider_pricing` table seeded from `cost/pricing.py` JSON with effective_date/version; tracker never hardcodes rates in logic.
- **Frontend**: Next.js App Router, dark graphite + violet/blue, Tailwind, Recharts, React Flow, WS live updates with polling fallback.

## State Schema (LangGraph)
`ExecutionState`: execution_id, objective, plan (list[PlanStep]), current_step_idx, statuses, tool_results, cost_so_far, tokens_so_far, retries_used, approvals_pending, mode, limits, correlation_id, error, partial_result. Checkpoints saved after every node.
