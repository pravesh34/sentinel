"""Versioned REST API. Routes stay thin — delegate to services."""
import uuid
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from ...database.session import get_db
from ...models.entities import (User, Execution, ApprovalRequest, ToolRegistryRow, BudgetLimit,
                                ApiCredential, CostRecord, AuditLog, ExecutionStep, ToolInvocation)
from ...schemas.schemas import (RegisterIn, LoginIn, TokenOut, UserOut, CreateExecutionIn, ExecutionOut,
                                ApprovalOut, ToolOut, ToolPermIn, BudgetIn, BudgetOut, CredentialIn, ApprovalDecision)
from ...services.security import hash_password, verify_password, create_access_token, encrypt_secret
from ...api.deps import get_current_user
from ...services.task_service import TaskService
from ...services.state_manager import HotStateStore
from ...config import settings
from ...approvals.manager import is_valid_approval
from ...tools.registry import build_default_registry

router = APIRouter()
hot_state = HotStateStore(settings.redis_url)
registry = build_default_registry()

# ---------- Auth ----------
@router.post("/auth/register", response_model=TokenOut)
def register(payload: RegisterIn, db: Session = Depends(get_db)):
    if db.query(User).filter_by(email=payload.email).first():
        raise HTTPException(409, "email exists")
    user = User(id=str(uuid.uuid4()), email=payload.email, hashed_password=hash_password(payload.password))
    db.add(user); db.commit()
    return TokenOut(access_token=create_access_token(user.id))

@router.post("/auth/login", response_model=TokenOut)
def login(payload: LoginIn, db: Session = Depends(get_db)):
    user = db.query(User).filter_by(email=payload.email.strip().lower()).first()
    if not user or not verify_password(payload.password, user.hashed_password):
        raise HTTPException(401, "bad credentials")
    return TokenOut(access_token=create_access_token(user.id))

@router.get("/auth/me", response_model=UserOut)
def me(user: User = Depends(get_current_user)):
    return UserOut(id=user.id, email=user.email, plan=user.plan)

@router.post("/auth/credentials")
def add_credential(payload: CredentialIn, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    db.add(ApiCredential(user_id=user.id, provider=payload.provider.lower(), encrypted_key=encrypt_secret(payload.api_key),
                         base_url=payload.base_url, is_default=payload.is_default))
    db.commit()
    return {"ok": True, "note": "key stored encrypted, never returned"}

@router.get("/auth/credentials")
def list_credentials(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """List providers without ever returning key material."""
    return [{"provider": c.provider, "base_url": c.base_url or "", "is_default": bool(c.is_default),
             "key_hint": "●●●● (stored encrypted)"}
            for c in db.query(ApiCredential).filter_by(user_id=user.id).all()]

# ---------- Executions ----------
@router.post("/executions", response_model=ExecutionOut)
async def create_execution(payload: CreateExecutionIn, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    svc = TaskService(db, hot_state)
    execution = await svc.create_and_run(user.id, payload)
    return ExecutionOut(id=execution.id, objective=execution.objective, status=execution.status, mode=execution.mode,
                        total_cost=execution.total_cost or 0.0, total_tokens=execution.total_tokens or 0,
                        correlation_id=execution.correlation_id or "", result=execution.result, error=execution.error)

@router.get("/executions", response_model=list[ExecutionOut])
def list_executions(status: str | None = Query(None), user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    q = db.query(Execution).filter_by(user_id=user.id)
    if status: q = q.filter_by(status=status)
    return [ExecutionOut(id=e.id, objective=e.objective, status=e.status, mode=e.mode, total_cost=e.total_cost or 0.0,
                         total_tokens=e.total_tokens or 0, correlation_id=e.correlation_id or "", result=e.result, error=e.error)
            for e in q.order_by(Execution.created_at.desc()).limit(50).all()]

@router.get("/executions/{eid}", response_model=ExecutionOut)
def get_execution(eid: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    e = db.query(Execution).filter_by(id=eid, user_id=user.id).first()
    if not e: raise HTTPException(404, "not found")
    return ExecutionOut(id=e.id, objective=e.objective, status=e.status, mode=e.mode, total_cost=e.total_cost or 0.0,
                        total_tokens=e.total_tokens or 0, correlation_id=e.correlation_id or "", result=e.result, error=e.error)

@router.post("/executions/{eid}/cancel")
def cancel_execution(eid: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    e = db.query(Execution).filter_by(id=eid, user_id=user.id).first()
    if not e: raise HTTPException(404, "not found")
    TaskService(db, hot_state).cancel(e)
    return {"status": e.status}

@router.post("/executions/{eid}/resume")
async def resume_execution(eid: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    e = db.query(Execution).filter_by(id=eid, user_id=user.id).first()
    if not e: raise HTTPException(404, "not found")
    e = await TaskService(db, hot_state).resume(e)
    return {"status": e.status, "result": e.result, "error": e.error}

@router.get("/executions/{eid}/trace")
def trace(eid: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    e = db.query(Execution).filter_by(id=eid, user_id=user.id).first()
    if not e: raise HTTPException(404, "not found")
    steps = db.query(ExecutionStep).filter_by(execution_id=eid).all()
    invocations = db.query(ToolInvocation).filter_by(execution_id=eid).all()
    audits = db.query(AuditLog).filter_by(execution_id=eid).order_by(AuditLog.created_at).all()
    return {"execution": {"id": e.id, "status": e.status, "cost": e.total_cost, "tokens": e.total_tokens,
                          "correlation_id": e.correlation_id},
            "steps": [{"step_id": s.step_id, "tool": s.tool_id, "status": s.status, "risk": s.risk_level} for s in steps],
            "tool_calls": [{"tool": i.tool_id, "status": i.status, "cost": i.cost, "duration_ms": i.duration_ms} for i in invocations],
            "audit": [{"action": a.action, "detail": a.detail, "at": a.created_at.isoformat() if a.created_at else ""} for a in audits]}

@router.get("/executions/{eid}/cost")
def cost(eid: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    e = db.query(Execution).filter_by(id=eid, user_id=user.id).first()
    if not e: raise HTTPException(404, "not found")
    records = db.query(CostRecord).filter_by(execution_id=eid).all()
    return {"execution_id": eid, "total_cost": e.total_cost or 0.0, "total_tokens": e.total_tokens or 0,
            "llm_input_tokens": sum(r.input_tokens or 0 for r in records),
            "llm_output_tokens": sum(r.output_tokens or 0 for r in records),
            "records": [{"provider": r.provider, "model": r.model, "cost": r.cost, "tokens": r.total_tokens,
                         "input_tokens": r.input_tokens or 0, "output_tokens": r.output_tokens or 0,
                         "estimated": bool(r.estimated)} for r in records]}

# ---------- Approvals ----------
@router.get("/approvals", response_model=list[ApprovalOut])
def list_approvals(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    rows = db.query(ApprovalRequest).join(Execution, Execution.id == ApprovalRequest.execution_id).filter(Execution.user_id == user.id).all()
    return [ApprovalOut(id=a.id, execution_id=a.execution_id, step_id=a.step_id, tool_id=a.tool_id,
                        risk_level=a.risk_level, status=a.status, args=a.args or {}) for a in rows]

@router.post("/approvals/{aid}/approve")
def decide_approval(aid: str, payload: ApprovalDecision, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    a = db.query(ApprovalRequest).filter_by(id=aid).first()
    if not a: raise HTTPException(404, "not found")
    e = db.query(Execution).filter_by(id=a.execution_id, user_id=user.id).first()
    if not e: raise HTTPException(404, "not found")
    if payload.decision == "approve":
        a.status = "approved"; a.decided_at = datetime.now(timezone.utc)
    else:
        a.status = "rejected"; a.decided_at = datetime.now(timezone.utc)
        e.status = "cancelled"; e.error = "approval rejected"
    db.commit()
    return {"status": a.status}

@router.post("/approvals/{aid}/reject")
def reject_approval(aid: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return decide_approval(aid, ApprovalDecision(decision="reject"), user, db)

# ---------- Tools ----------
@router.get("/tools", response_model=list[ToolOut])
def list_tools(db: Session = Depends(get_db)):
    # Seed DB on first call
    if db.query(ToolRegistryRow).count() == 0:
        for t in registry.list_tools():
            db.add(ToolRegistryRow(tool_id=t.tool_id, name=t.name, description=t.description,
                                   input_schema=t.input_schema, risk_level=t.risk_level, timeout_s=t.timeout_s))
        db.commit()
    return [ToolOut(tool_id=r.tool_id, name=r.name, description=r.description, risk_level=r.risk_level,
                    enabled=bool(r.enabled), timeout_s=r.timeout_s) for r in db.query(ToolRegistryRow).all()]

@router.get("/tools/{tid}")
def get_tool(tid: str, db: Session = Depends(get_db)):
    r = db.query(ToolRegistryRow).filter_by(tool_id=tid).first()
    if not r: raise HTTPException(404, "not found")
    return {"tool_id": r.tool_id, "name": r.name, "risk_level": r.risk_level, "input_schema": r.input_schema, "enabled": r.enabled}

@router.patch("/tools/{tid}/permissions")
def patch_tool(tid: str, payload: ToolPermIn, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    r = db.query(ToolRegistryRow).filter_by(tool_id=tid).first()
    if not r: raise HTTPException(404, "not found")
    if payload.enabled is not None: r.enabled = payload.enabled
    if payload.timeout_s is not None: r.timeout_s = payload.timeout_s
    db.commit()
    return {"tool_id": tid, "enabled": r.enabled}

# ---------- Budgets ----------
@router.get("/budgets", response_model=list[BudgetOut])
def list_budgets(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return [BudgetOut(id=b.id, scope=b.scope, max_cost=b.max_cost, max_tokens=b.max_tokens)
            for b in db.query(BudgetLimit).filter_by(user_id=user.id).all()]

@router.post("/budgets", response_model=BudgetOut)
def create_budget(payload: BudgetIn, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    b = BudgetLimit(id=str(uuid.uuid4()), user_id=user.id, scope=payload.scope, max_cost=payload.max_cost, max_tokens=payload.max_tokens)
    db.add(b); db.commit()
    return BudgetOut(id=b.id, scope=b.scope, max_cost=b.max_cost, max_tokens=b.max_tokens)

@router.patch("/budgets/{bid}")
def patch_budget(bid: str, payload: BudgetIn, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    b = db.query(BudgetLimit).filter_by(id=bid, user_id=user.id).first()
    if not b: raise HTTPException(404, "not found")
    b.max_cost = payload.max_cost; b.max_tokens = payload.max_tokens; b.scope = payload.scope
    db.commit()
    return {"id": bid, "max_cost": b.max_cost}

# ---------- Analytics ----------
@router.get("/analytics/overview")
def overview(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    execs = db.query(Execution).filter_by(user_id=user.id).all()
    total = len(execs)
    ok = sum(1 for e in execs if e.status == "completed")
    fail = sum(1 for e in execs if e.status in ("failed", "cancelled", "budget_exceeded", "limit_exceeded"))
    spend = sum(e.total_cost or 0 for e in execs)
    tokens = sum(e.total_tokens or 0 for e in execs)
    return {"total": total, "successful": ok, "failed": fail, "success_rate": (ok / total if total else 0),
            "total_spend": round(spend, 4), "total_tokens": tokens, "data_source": "real DB aggregates (mock LLM if provider=mock)"}

@router.get("/analytics/costs")
def analytics_costs(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    rows = db.query(CostRecord).filter_by(user_id=user.id).all()
    by_provider: dict[str, float] = {}
    for r in rows: by_provider[r.provider] = by_provider.get(r.provider, 0) + (r.cost or 0)
    return {"by_provider": by_provider, "total": round(sum(by_provider.values()), 4)}

@router.get("/analytics/executions")
def analytics_execs(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    execs = db.query(Execution).filter_by(user_id=user.id).all()
    return {"executions": [{"id": e.id, "status": e.status, "cost": e.total_cost or 0} for e in execs]}
