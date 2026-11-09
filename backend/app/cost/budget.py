"""Budget reservation: check before paid op, reconcile after. Concurrency-safe via DB sums in service layer."""
from .tracker import CostTracker

class BudgetExceeded(Exception):
    pass

def can_afford(tracker: CostTracker, estimated_cost: float, max_cost: float) -> bool:
    return (tracker.total_cost + estimated_cost) <= max_cost

def check_or_raise(tracker: CostTracker, estimated_cost: float, max_cost: float):
    if not can_afford(tracker, estimated_cost, max_cost):
        raise BudgetExceeded(f"budget exceeded: {tracker.total_cost + estimated_cost:.4f} > {max_cost}")
