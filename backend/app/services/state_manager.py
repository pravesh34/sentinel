"""State persistence: PostgreSQL checkpoints + Redis hot-state with in-memory fallback."""
import json
try:
    import redis as redis_lib
except Exception:
    redis_lib = None  # type: ignore

class HotStateStore:
    """Redis-backed when available, else in-memory dict (dev/test)."""
    def __init__(self, redis_url: str = ""):
        self._mem: dict[str, str] = {}
        self._redis = None
        if redis_lib and redis_url:
            try:
                self._redis = redis_lib.from_url(redis_url, decode_responses=True)
                self._redis.ping()
            except Exception:
                self._redis = None
    def set(self, key: str, value: dict):
        payload = json.dumps(value, default=str)
        if self._redis:
            try: self._redis.setex(key, 3600, payload); return
            except Exception: self._redis = None
        self._mem[key] = payload
    def get(self, key: str) -> dict | None:
        if self._redis:
            try:
                v = self._redis.get(key)
                return json.loads(v) if v else None
            except Exception: self._redis = None
        v = self._mem.get(key)
        return json.loads(v) if v else None
    def delete(self, key: str):
        if self._redis:
            try: self._redis.delete(key); return
            except Exception: self._redis = None
        self._mem.pop(key, None)
