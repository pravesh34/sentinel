"""Deterministic hard limits — enforced in code, never by LLM prompts."""
from dataclasses import dataclass

@dataclass
class ExecutionLimits:
    max_steps: int = 20
    max_tool_calls: int = 30
    max_retries: int = 5
    max_runtime_s: int = 300
    max_concurrent_tools: int = 3
    max_replans: int = 3
    max_tokens: int = 20000
    max_cost: float = 1.0

    def check_pre_step(self, steps_done: int, tool_calls_done: int, elapsed_s: float, cost_so_far: float, tokens_so_far: int) -> str | None:
        """Return violation reason or None."""
        if steps_done >= self.max_steps: return "limit_exceeded: max_steps"
        if tool_calls_done >= self.max_tool_calls: return "limit_exceeded: max_tool_calls"
        if elapsed_s > self.max_runtime_s: return "limit_exceeded: max_runtime"
        if cost_so_far >= self.max_cost: return "budget_exceeded: max_cost"
        if tokens_so_far >= self.max_tokens: return "budget_exceeded: max_tokens"
        return None

    def check_retry(self, retries_used: int) -> bool:
        return retries_used < self.max_retries
