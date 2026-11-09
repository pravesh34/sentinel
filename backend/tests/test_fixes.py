"""Tests for the 4 diagnosis fixes:
1. LLM usage → CostTracker (no placeholder)
2. Sandbox pre-flight (undefined names, print-only)
3. Live web_search shape (mock fallback without key)
4. Worker stale sweep"""
import asyncio
from datetime import datetime, timedelta, timezone
import pytest

def test_planner_usage_flows_to_cost():
    from app.cost.tracker import CostTracker
    from app.agents.planner import Planner
    from app.providers.base import MockLLM
    from app.tools.registry import build_default_registry
    planner = Planner(provider=MockLLM(), registry=build_default_registry())
    planner.plan("Calculate 1+1")
    assert planner.last_result is not None
    assert planner.last_result.input_tokens > 0
    assert planner.last_result.output_tokens > 0
    # Real spend recorded from planner usage, not a placeholder
    t = CostTracker(provider="groq", model="openai/gpt-oss-20b")
    t.record_llm(planner.last_result.input_tokens, planner.last_result.output_tokens, confirmed=True)
    assert t.total_tokens == planner.last_result.input_tokens + planner.last_result.output_tokens
    assert t.total_cost > 0  # real pricing lookup for groq

def test_sandbox_preflight_rejects_undefined():
    from app.tools.implementations.builtin import preflight_sandbox
    assert "undefined name" in preflight_sandbox("result = langgraph_summary")  # hallucinated var
    assert "undefined name" in preflight_sandbox("print(langgraph_summary)")
    assert "print-only" in preflight_sandbox('print("hi")')
    assert "empty" in preflight_sandbox("")
    assert "blocked import" in preflight_sandbox("import os\nresult=1")
    assert "syntax" in preflight_sandbox("def broken(:")
    assert preflight_sandbox("result = 2 + 2") is None
    assert preflight_sandbox("frameworks=['a']\nresult = len(frameworks)") is None

@pytest.mark.asyncio
async def test_sandbox_handler_uses_preflight():
    from app.tools.registry import build_default_registry
    reg = build_default_registry()
    out = await reg.invoke("python_sandbox", {"code": "print(langgraph_summary)"})
    assert "error" in out and "undefined" in out["error"]

@pytest.mark.asyncio
async def test_web_search_mock_without_key(monkeypatch):
    monkeypatch.delenv("TAVILY_API_KEY", raising=False)
    monkeypatch.delenv("SERPAPI_API_KEY", raising=False)
    from app.tools.registry import build_default_registry
    reg = build_default_registry()
    out = await reg.invoke("web_search", {"query": "test"})
    assert out["mock"] is True and out["results"]

def test_worker_sweep_stale():
    from app.database.session import SessionLocal
    from app.models.entities import Execution
    from app.worker import sweep_stale
    import uuid
    db = SessionLocal()
    eid = str(uuid.uuid4())
    old = datetime.now(timezone.utc) - timedelta(minutes=30)
    db.add(Execution(id=eid, user_id="sweep-test", objective="stale test", status="running",
                     max_runtime_s=60, started_at=old, created_at=old))
    db.add(Execution(id=str(uuid.uuid4()), user_id="sweep-test", objective="fresh test", status="running",
                     max_runtime_s=600, started_at=datetime.now(timezone.utc), created_at=datetime.now(timezone.utc)))
    db.commit()
    swept = sweep_stale(db)
    assert eid in swept
    row = db.query(Execution).filter_by(id=eid).first()
    assert row.status == "failed" and "stale" in row.error
    db.delete(row); db.commit(); db.close()

def test_cost_endpoint_shows_llm_tokens(client, auth):
    r = client.post("/api/v1/executions", headers=auth, json={
        "objective": "Summarize hi", "mode": "supervised", "provider": "mock", "model": "mock-llm-1"})
    eid = r.json()["id"]
    c = client.get(f"/api/v1/executions/{eid}/cost", headers=auth)
    assert c.status_code == 200
    body = c.json()
    assert "llm_input_tokens" in body and "llm_output_tokens" in body
    # Mock planner recorded real (non-placeholder) usage
    assert body["llm_input_tokens"] > 0
