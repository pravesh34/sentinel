import asyncio
import pytest
from app.tools.registry import build_default_registry

@pytest.mark.asyncio
async def test_calculator():
    reg = build_default_registry()
    assert (await reg.invoke("calculator", {"expression": "2+3*4"}))["result"] == 14

@pytest.mark.asyncio
async def test_summarizer():
    reg = build_default_registry()
    out = await reg.invoke("summarizer", {"text": "Cats are great. They sleep a lot. Dogs are loyal."})
    assert "Cats" in out["summary"]

@pytest.mark.asyncio
async def test_json_parser():
    reg = build_default_registry()
    assert (await reg.invoke("json_parser", {"text": '{"a": 1}'}))["parsed"] == {"a": 1}

@pytest.mark.asyncio
async def test_unknown_tool_rejected():
    reg = build_default_registry()
    with pytest.raises(KeyError):
        await reg.invoke("rm_rf", {})

@pytest.mark.asyncio
async def test_sandbox_blocks_dangerous_import():
    reg = build_default_registry()
    out = await reg.invoke("python_sandbox", {"code": "import os\nresult=1"})
    assert "blocked" in out["error"]

@pytest.mark.asyncio
async def test_sandbox_allows_safe_code():
    reg = build_default_registry()
    out = await reg.invoke("python_sandbox", {"code": "result = 2+2"})
    assert out["output"] == 4

@pytest.mark.asyncio
async def test_web_search_mock_labeled():
    reg = build_default_registry()
    out = await reg.invoke("web_search", {"query": "agentic AI"})
    assert out["mock"] is True  # clearly labeled, not fabricated live data
