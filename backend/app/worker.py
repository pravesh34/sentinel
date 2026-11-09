"""Worker entrypoint: resumes interrupted executions from checkpoints on startup.

Stale sweep: executions still in 'running' whose elapsed wall time exceeds
their max_runtime_s are marked failed (timeout) instead of resumed — they
cannot complete within their own budget.
'Awaiting_approval' rows are left paused for a human.
"""
import asyncio
from datetime import datetime, timezone
from .database.session import SessionLocal, init_db
from .models.entities import Execution
from .services.task_service import TaskService

def sweep_stale(db, now: datetime | None = None) -> list[str]:
    """Mark stale 'running' executions as failed. Returns swept ids."""
    now = now or datetime.now(timezone.utc)
    swept = []
    for e in db.query(Execution).filter(Execution.status == "running").all():
        started = e.started_at or e.created_at
        if not started:
            continue
        # Normalize naive/aware datetimes (SQLite returns naive UTC)
        if started.tzinfo is None:
            started = started.replace(tzinfo=timezone.utc)
        elapsed = (now - started).total_seconds()
        if elapsed > (e.max_runtime_s or 300):
            e.status = "failed"
            e.error = f"stale: exceeded max_runtime {e.max_runtime_s}s on worker restart (elapsed {elapsed:.0f}s)"
            e.finished_at = now
            e.result = {"partial": True, "failure_reason": e.error}
            swept.append(e.id)
            print(f"[worker] swept stale {e.id} (elapsed {elapsed:.0f}s > limit {e.max_runtime_s}s)")
    if swept:
        db.commit()
    return swept

async def recover_interrupted():
    init_db()
    db = SessionLocal()
    swept = sweep_stale(db)
    stuck = db.query(Execution).filter(Execution.status.in_(["running", "awaiting_approval"])).all()
    for e in stuck:
        print(f"[worker] resuming {e.id} from checkpoint (status={e.status})")
        if e.status == "running":
            try:
                await TaskService(db).resume(e)
            except Exception as exc:
                print(f"[worker] resume failed for {e.id}: {exc}")
    db.close()

if __name__ == "__main__":
    asyncio.run(recover_interrupted())
