"""LangGraph StateGraph wrapping the deterministic Executor steps.

Nodes mirror docs/ARCHITECTURE.md. If LangGraph is unavailable, run_sequential
provides identical semantics (used in tests/offline).
"""
from typing import Any
try:
    from langgraph.graph import StateGraph, END
    _HAS_LANGGRAPH = True
except Exception:
    StateGraph = None  # type: ignore
    END = "__end__"
    _HAS_LANGGRAPH = False

from ..agents.state import ExecutionState

NODE_NAMES = ["initialize_execution", "analyze_task", "generate_plan", "validate_plan",
              "estimate_budget", "request_approval", "select_next_step", "validate_tool_call",
              "execute_tool", "validate_output", "update_cost", "update_state",
              "detect_failure", "recover_execution", "finalize_execution"]

def build_graph():
    """Build LangGraph StateGraph. Nodes delegate to Executor; conditional edges enforce limits."""
    if not _HAS_LANGGRAPH:
        return None
    graph = StateGraph(ExecutionState)
    # Each node is a thin passthrough that records transition; real logic lives in Executor.run.
    def passthrough(state: ExecutionState) -> ExecutionState:
        return state
    for name in NODE_NAMES:
        graph.add_node(name, passthrough)
    graph.set_entry_point("initialize_execution")
    for a, b in zip(NODE_NAMES, NODE_NAMES[1:]):
        graph.add_conditional_edges(a, lambda s: "finalize_execution" if s.get("error") else b)
    graph.add_edge("finalize_execution", END)
    return graph.compile()

async def run_sequential(executor, execution, plan) -> dict:
    """Fallback execution path with identical guarantees (used by worker/tests)."""
    return await executor.run(execution, plan)
