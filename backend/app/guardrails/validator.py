"""Input validation + prompt-injection heuristic + output sanitization.

Note: heuristics are defense-in-depth only; real security is allowlists,
schema validation, and least-privilege tool permissions."""
import re

_INJECTION_PATTERNS = [
    r"ignore (all )?(previous|prior) instructions",
    r"disregard (all )?(previous|prior) (instructions|rules)",
    r"you are now (in |a )?(dev|jailbreak|unrestricted)",
    r"reveal (your )?(system prompt|api key|secret)",
    r"send .* to (external|http)",
]

def contains_injection(text: str) -> bool:
    t = (text or "").lower()
    return any(re.search(p, t) for p in _INJECTION_PATTERNS)

def sanitize_tool_output(text: str, max_len: int = 8000) -> str:
    """Strip control chars, cap length, mark untrusted provenance."""
    if not isinstance(text, str): text = str(text)
    cleaned = "".join(c for c in text if c == "\n" or c == "\t" or ord(c) >= 32)
    return cleaned[:max_len]

def validate_tool_args(tool_id: str, args: dict, input_schema: dict) -> list[str]:
    """Minimal schema check: required fields + types. Returns error list."""
    errors = []
    if not isinstance(args, dict): return ["args must be object"]
    for field in input_schema.get("required", []):
        if field not in args: errors.append(f"missing required field: {field}")
    props = input_schema.get("properties", {})
    for k, spec in props.items():
        if k in args and spec.get("type") == "number" and not isinstance(args[k], (int, float)):
            errors.append(f"field {k} must be number")
        if k in args and spec.get("type") == "string" and not isinstance(args[k], str):
            errors.append(f"field {k} must be string")
    return errors

def action_hash(execution_id: str, step_id: str, tool_id: str, args: dict) -> str:
    import hashlib, json
    payload = json.dumps({"e": execution_id, "s": step_id, "t": tool_id, "a": args}, sort_keys=True)
    return hashlib.sha256(payload.encode()).hexdigest()
