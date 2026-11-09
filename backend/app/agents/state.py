from typing import TypedDict, Any
from ..schemas.schemas import ExecutionPlan

class ExecutionState(TypedDict, total=False):
    execution_id: str
    user_id: str
    objective: str
    correlation_id: str
    plan: ExecutionPlan | None
    current_step_idx: int
    step_statuses: dict[str, str]
    tool_results: dict[str, Any]
    tool_calls_done: int
    retries_used: int
    replans_used: int
    total_cost: float
    total_tokens: int
    mode: str
    max_steps: int
    max_tool_calls: int
    max_cost: float
    max_tokens: int
    max_runtime_s: int
    allowed_tools: list[str]
    provider: str
    model: str
    started_at: float
    error: str | None
    committed_idempotency_keys: list[str]
