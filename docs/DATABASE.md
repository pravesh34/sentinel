# SENTINEL — Database (PostgreSQL, UUID PKs, JSONB, enums→VARCHAR+CHECK)

- `users(id, email, hashed_password, plan, created_at)`
- `api_credentials(id, user_id FK, provider, encrypted_key, base_url, is_default)` — Fernet AES, never plaintext/logged.
- `executions(id, user_id FK, objective, status[queued,running,awaiting_approval,completed,failed,cancelled,budget_exceeded,limit_exceeded], mode, complexity, max_steps, max_tool_calls, max_cost, max_runtime_s, max_tokens, provider, model, total_cost, total_tokens, started_at, finished_at, error, correlation_id)`
- `execution_plans(id, execution_id FK, steps JSONB, estimated_cost, created_at)`
- `execution_steps(id, execution_id FK, step_id, description, tool_id, status, args JSONB, result JSONB, estimated_cost, actual_cost, risk_level, retries, started_at, finished_at, error)`
- `tool_registry(id/tool_id, name, description, input_schema JSONB, risk_level, enabled, timeout_s, max_retries)`
- `tool_invocations(id, execution_id FK, step_id, tool_id, idempotency_key UNIQUE, args JSONB, result JSONB, status, duration_ms, cost, created_at)`
- `cost_records(id, execution_id FK, user_id FK, provider, model, input_tokens, output_tokens, total_tokens, cost, estimated, created_at)`
- `budget_limits(id, user_id FK, scope[execution|daily|monthly], max_cost, max_tokens, period_start)`
- `execution_checkpoints(id, execution_id FK, state JSONB, step_idx, created_at)` — latest valid resumed on restart.
- `approval_requests(id, execution_id FK, step_id, tool_id, action_hash, args JSONB, risk_level, status[pending,approved,rejected,expired], expires_at, decided_at)`
- `audit_logs(id, execution_id, actor, action, detail JSONB, correlation_id, created_at)`
- `provider_pricing(provider, model, input_per_1k, output_per_1k, version, effective_date, PK(provider,model,version))`
- `execution_errors(id, execution_id FK, step_id, error_type, message, retryable, created_at)`

Indexes: executions(user_id,status,created_at), steps(execution_id), invocations(idempotency_key), cost(user_id,created_at), audit(execution_id). Migrations: Alembic (`backend/migrations/`). Dev/test: SQLAlchemy `create_all` on SQLite.
