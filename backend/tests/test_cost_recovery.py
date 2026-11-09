import asyncio
import pytest
from app.cost.tracker import CostTracker
from app.cost.budget import can_afford, check_or_raise, BudgetExceeded
from app.cost.pricing import cost_for
from app.recovery.manager import with_retry, should_retry, partial_result
from app.providers.base import MockLLM

def test_pricing_math():
    assert cost_for("openai", "gpt-4o-mini", 1000, 1000) > 0
    assert cost_for("mock", "mock-llm-1", 1000, 1000) == 0.0

def test_tracker_aggregation():
    t = CostTracker(provider="openai", model="gpt-4o-mini")
    t.record_llm(1000, 500); t.record_llm(500, 250)
    assert t.total_tokens == 2250  # (1000+500)+(500+250)
    assert t.total_cost > 0

def test_budget_enforcement():
    t = CostTracker(); t.total_cost = 0.9
    assert not can_afford(t, 0.2, 1.0)
    with pytest.raises(BudgetExceeded):
        check_or_raise(t, 0.2, 1.0)

def test_budget_warnings():
    t = CostTracker(); t.total_cost = 0.8
    assert t.warning_level(1.0) == "75%"

def test_mock_llm_deterministic_tokens():
    llm = MockLLM()
    r1 = llm.chat([{"role": "user", "content": "hello"}])
    r2 = llm.chat([{"role": "user", "content": "hello"}])
    assert r1.input_tokens == r2.input_tokens and r1.provider == "mock"

@pytest.mark.asyncio
async def test_retry_then_success():
    calls = {"n": 0}
    async def flaky():
        calls["n"] += 1
        if calls["n"] < 3: raise TimeoutError("timeout")
        return "ok"
    assert await with_retry(flaky, max_retries=3) == "ok"

@pytest.mark.asyncio
async def test_retry_exhaustion_raises():
    async def always_fail(): raise RuntimeError("boom")
    with pytest.raises(RuntimeError):
        await with_retry(always_fail, max_retries=1)

def test_no_retry_permanent():
    assert should_retry("invalid_args", False, 0, 5) is False
    assert should_retry("timeout", True, 5, 5) is False

def test_partial_result():
    pr = partial_result([{"step_id": "s1"}], "timeout")
    assert pr["partial"] is True
