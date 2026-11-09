"""Bounded recovery: exponential backoff, checkpoint resume, partial results."""
import asyncio

async def with_retry(fn, max_retries: int = 2, base_delay: float = 0.05, retry_after: float | None = None):
    delay = retry_after if retry_after is not None else base_delay
    last_exc = None
    attempts = 0
    for attempt in range(max_retries + 1):
        try:
            return await fn()
        except Exception as e:
            last_exc = e
            attempts += 1
            if attempt >= max_retries: break
            await asyncio.sleep(min(delay * (2 ** attempt), 2.0))
    raise last_exc  # type: ignore

def should_retry(error_type: str, retryable: bool, retries_used: int, max_retries: int) -> bool:
    if not retryable: return False
    if retries_used >= max_retries: return False
    permanent = {"invalid_args", "unauthorized", "budget_exceeded", "limit_exceeded", "validation"}
    return error_type not in permanent

def partial_result(completed: list[dict], failure: str) -> dict:
    return {"completed_steps": completed, "partial": True, "failure_reason": failure,
            "note": "Partial result: full execution was not possible within limits."}
