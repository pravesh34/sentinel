"""Risk classification + permission policy. LOW may auto-run; HIGH/CRITICAL need approval."""
RISK_ORDER = {"LOW": 0, "MEDIUM": 1, "HIGH": 2, "CRITICAL": 3}

def requires_approval(risk: str, mode: str) -> bool:
    if risk == "CRITICAL":
        return True  # autonomous never overrides CRITICAL
    if mode == "manual":
        return True
    if mode == "supervised":
        return risk in ("HIGH", "CRITICAL")
    if mode == "autonomous":
        return risk == "CRITICAL"
    return True

def is_allowed(tool_id: str, allowed_tools: list[str], enabled: bool, risk: str) -> bool:
    if not enabled: return False
    if allowed_tools and tool_id not in allowed_tools: return False
    return True
