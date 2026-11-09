"""Cost tracker: estimated vs confirmed, per-call/step/run aggregation."""
from dataclasses import dataclass, field
from . import pricing

@dataclass
class CostTracker:
    provider: str = "mock"
    model: str = "mock-llm-1"
    records: list[dict] = field(default_factory=list)
    total_cost: float = 0.0
    total_tokens: int = 0

    def record_llm(self, input_tokens: int, output_tokens: int, confirmed: bool = True, duration_ms: int = 0):
        cost = pricing.cost_for(self.provider, self.model, input_tokens, output_tokens)
        rec = {"provider": self.provider, "model": self.model, "input_tokens": input_tokens,
               "output_tokens": output_tokens, "total_tokens": input_tokens + output_tokens,
               "cost": round(cost, 6), "estimated": not confirmed, "duration_ms": duration_ms}
        self.records.append(rec)
        self.total_cost += cost
        self.total_tokens += input_tokens + output_tokens
        return rec

    def record_tool(self, tool_id: str, cost: float = 0.0, estimated: bool = False):
        rec = {"tool": tool_id, "cost": round(cost, 6), "estimated": estimated}
        self.records.append(rec)
        self.total_cost += cost
        return rec

    def budget_fraction(self, max_cost: float) -> float:
        return self.total_cost / max_cost if max_cost > 0 else 0.0

    def warning_level(self, max_cost: float) -> str | None:
        f = self.budget_fraction(max_cost)
        if f >= 1.0: return "100%"
        if f >= 0.9: return "90%"
        if f >= 0.75: return "75%"
        return None
