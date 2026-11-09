"""Central Tool Registry — the ONLY path for tool execution."""
import asyncio
from dataclasses import dataclass, field
from typing import Any, Callable

@dataclass
class ToolDef:
    tool_id: str
    name: str
    description: str
    input_schema: dict
    risk_level: str  # LOW|MEDIUM|HIGH|CRITICAL
    timeout_s: int = 30
    max_retries: int = 2
    handler: Callable | None = None
    cost_fn: Callable[[dict], float] | None = None
    irreversible: bool = False

class ToolRegistry:
    def __init__(self):
        self._tools: dict[str, ToolDef] = {}

    def register(self, tool: ToolDef):
        self._tools[tool.tool_id] = tool

    def get(self, tool_id: str) -> ToolDef | None:
        return self._tools.get(tool_id)

    def list_tools(self) -> list[ToolDef]:
        return list(self._tools.values())

    def estimate_cost(self, tool_id: str, args: dict) -> float:
        t = self.get(tool_id)
        if t and t.cost_fn: return t.cost_fn(args)
        return 0.0

    async def invoke(self, tool_id: str, args: dict, timeout_override: int | None = None) -> dict[str, Any]:
        tool = self.get(tool_id)
        if not tool: raise KeyError(f"unknown tool: {tool_id}")
        if not tool.handler: raise RuntimeError(f"tool {tool_id} has no handler")
        timeout = timeout_override or tool.timeout_s
        result = await asyncio.wait_for(tool.handler(args), timeout=timeout)
        return result

def build_default_registry() -> ToolRegistry:
    from .implementations import builtin
    reg = ToolRegistry()
    for tool in builtin.all_tools():
        reg.register(tool)
    return reg

# Singleton for app use
registry = build_default_registry()
