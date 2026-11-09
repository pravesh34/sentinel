# SENTINEL — Deployment

Local (macOS): `docker compose up --build` → frontend http://localhost:3000, API http://localhost:8000/docs, nginx http://localhost:8080.
Dev without Docker: `cd backend && pip install -e ".[dev]" && uvicorn app.main:app --reload` (SQLite fallback) + `cd frontend && npm install && npm run dev`.
Prod: set strong SECRET_KEY + Fernet ENCRYPTION_KEY, use PostgreSQL + Redis via compose, run Alembic migrations (`alembic upgrade head`), enable LangSmith keys optionally, put nginx/TLS in front, use read-only DB roles for db_query, rotate pricing table via ProviderPricing rows.
Health: /health, /health/ready (DB ping). Worker: `python -m app.worker` resumes interrupted runs from checkpoints.
Never commit .env / real API keys; see .env.example.
