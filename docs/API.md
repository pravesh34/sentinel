# SENTINEL — API (OpenAPI at /docs when running)

Auth: `POST /api/v1/auth/register`, `POST /api/v1/auth/login`, `GET /api/v1/auth/me`, `POST /api/v1/auth/credentials {provider, api_key, base_url?, is_default?}` (Fernet-encrypted, key never returned), `GET /api/v1/auth/credentials` (providers only, no key material). Per-user credential for the requested execution provider is decrypted and used for that run; falls back to server env keys (`OPENAI_API_KEY` etc. / `DEFAULT_PROVIDER` / `FALLBACK_PROVIDER`).
Executions: `POST /api/v1/executions {objective, mode, max_steps, max_tool_calls, max_cost, max_runtime_s, max_tokens, allowed_tools, provider, model}`, `GET /api/v1/executions[?status=]`, `GET /api/v1/executions/{id}`, `POST /{id}/cancel`, `POST /{id}/resume`, `GET /{id}/trace`, `GET /{id}/cost`.
Approvals: `GET /api/v1/approvals`, `POST /api/v1/approvals/{id}/approve|reject {decision}`.
Tools: `GET /api/v1/tools`, `GET /api/v1/tools/{id}`, `PATCH /api/v1/tools/{id}/permissions {enabled, timeout_s}`.
Budgets: `GET/POST /api/v1/budgets`, `PATCH /api/v1/budgets/{id}`.
Analytics: `GET /api/v1/analytics/overview|costs|executions`. Health: `/health`, `/health/ready`. WS: `ws://host/ws/executions/{id}` (polling fallback in UI).
Auth: `Authorization: Bearer <JWT>`. Errors: 401/404/409 + `x-correlation-id` header on every response.
