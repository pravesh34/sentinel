"""Worker entrypoint: resumes interrupted executions from checkpoints on startup."""
import asyncio
from .database.session import SessionLocal, init_db
from .models.entities import Execution
from .services.task_service import TaskService

async def recover_interrupted():
    init_db()
    db = SessionLocal()
    stuck = db.query(Execution).filter(Execution.status.in_(["running", "awaiting_approval"])).all()
    for e in stuck:
        print(f"[worker] resuming {e.id} from checkpoint (status={e.status})")
        # awaiting_approval stays paused for human; only auto-resume 'running'
        if e.status == "running":
            try:
                await TaskService(db).resume(e)
            except Exception as exc:
                print(f"[worker] resume failed for {e.id}: {exc}")
    db.close()

if __name__ == "__main__":
    asyncio.run(recover_interrupted())
