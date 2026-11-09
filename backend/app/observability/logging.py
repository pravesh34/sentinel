import json, logging, uuid
from contextvars import ContextVar
from datetime import datetime, timezone

correlation_id_ctx: ContextVar[str] = ContextVar("correlation_id", default="-")

class JsonFormatter(logging.Formatter):
    def format(self, record):
        payload = {
            "ts": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "correlation_id": correlation_id_ctx.get(),
            "message": record.getMessage(),
        }
        if record.exc_info:
            payload["exc_info"] = self.formatException(record.exc_info)
        return json.dumps(payload)

def setup_logging(level="INFO"):
    handler = logging.StreamHandler()
    handler.setFormatter(JsonFormatter())
    root = logging.getLogger()
    root.handlers = [handler]
    root.setLevel(level)

def new_correlation_id() -> str:
    return str(uuid.uuid4())

def get_logger(name: str):
    return logging.getLogger(name)
