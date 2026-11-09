"""HITL approvals bound to exact action hash. Expire after 10 min."""
from datetime import datetime, timezone, timedelta
from ..guardrails.validator import action_hash

APPROVAL_TTL_MIN = 10

def make_approval(execution_id: str, step_id: str, tool_id: str, args: dict, risk: str, reason: str = "") -> dict:
    expires = datetime.now(timezone.utc) + timedelta(minutes=APPROVAL_TTL_MIN)
    return {"execution_id": execution_id, "step_id": step_id, "tool_id": tool_id,
            "action_hash": action_hash(execution_id, step_id, tool_id, args),
            "args": args, "risk_level": risk, "reason": reason, "status": "pending",
            "expires_at": expires.isoformat()}

def is_valid_approval(approval: dict, execution_id: str, step_id: str, tool_id: str, args: dict) -> bool:
    if approval.get("status") != "approved": return False
    exp = approval.get("expires_at", "")
    try:
        if datetime.fromisoformat(exp) < datetime.now(timezone.utc): return False
    except Exception:
        return False
    expected = action_hash(execution_id, step_id, tool_id, args)
    return approval.get("action_hash") == expected
