"""Task Manager service: thin orchestration, no business logic in routes."""
import asyncio
import time
import uuid
from datetime import datetime, timezone
from ..models.entities import Execution, ExecutionPlan, ExecutionStep, CostRecord, ExecutionCheckpoint, AuditLog
from ..agents.planner import Planner
from ..agents.executor import Executor, ApprovalPending
from ..providers.base import get_provider
from ..models.entities import ApiCredential
from ..services.security import decrypt_secret
from ..config import settings
from ..tools.registry import build_default_registry
from ..observability.logging import correlation_id_ctx, get_logger
from ..workflows.execution_graph import run_sequential

log = get_logger("sentinel.task")

class TaskService:
    def __init__(self, db, hot_state=None):
        self.db = db
        self.hot_state = hot_state
        self.registry = build_default_registry()

    async def create_and_run(self, user_id: str, payload) -> Execution:
        execution = Execution(
            id=str(uuid.uuid4()), user_id=user_id, objective=payload.objective, mode=payload.mode,
            max_steps=payload.max_steps, max_tool_calls=payload.max_tool_calls, max_cost=payload.max_cost,
            max_runtime_s=payload.max_runtime_s, max_tokens=payload.max_tokens,
            allowed_tools=payload.allowed_tools, provider=payload.provider, model=payload.model,
            status="running", correlation_id=correlation_id_ctx.get(),
        )
        self.db.add(execution); self.db.commit(); self.db.refresh(execution)

        # Resolve API key: per-user credential (default for provider) → env fallback → mock
        api_key, base_url = self._resolve_key(user_id, payload.provider)
        providers = [get_provider(payload.provider, api_key, base_url)]
        if settings.fallback_provider and settings.fallback_provider != payload.provider:
            providers.append(get_provider(settings.fallback_provider))
        plan, last_err = None, None
        for prov in providers:
            try:
                plan = Planner(provider=prov, registry=self.registry).plan(
                    payload.objective, model=payload.model, allowed_tools=payload.allowed_tools)
                break
            except Exception as e:  # noqa: BLE001 — fallthrough to next provider
                last_err = e
                log.warning("provider %s failed: %s", prov.name, e)
        if plan is None:
            execution.status = "failed"; execution.error = f"planning failed: {last_err}"; self.db.commit()
            return execution

        # Validate plan against limits before execution
        if len(plan.steps) > execution.max_steps:
            # Truncate is NOT silent: mark limit_exceeded with partial info
            execution.status = "limit_exceeded"
            execution.error = f"plan has {len(plan.steps)} steps > max_steps {execution.max_steps}"
            self.db.commit()
            return execution

        self.db.add(ExecutionPlan(execution_id=execution.id, steps=[s.model_dump() for s in plan.steps],
                                  estimated_cost=plan.estimated_cost))
        for s in plan.steps:
            self.db.add(ExecutionStep(execution_id=execution.id, step_id=s.step_id, description=s.description,
                                      tool_id=s.selected_tool, args=s.args, estimated_cost=s.estimated_cost,
                                      risk_level=s.risk_level))
        self.db.commit()

        self._checkpoint(execution, {"plan": [s.model_dump() for s in plan.steps], "step_idx": 0})
        executor = Executor(self.registry, self.db, self.hot_state)
        try:
            result = await run_sequential(executor, execution, plan)
            if execution.status not in ("completed",):
                # partial/budget/limit already set by executor
                pass
            else:
                execution.result = result
            self._record_cost(execution)
            self._checkpoint(execution, {"result_status": execution.status})
        except ApprovalPending as e:
            execution.status = "awaiting_approval"
            self.db.commit()
            log.info("execution %s awaiting approval %s", execution.id, e.approval_id)
        except Exception as e:
            execution.status = "failed"; execution.error = str(e); self.db.commit()
            log.exception("execution failed")
        return execution

    async def resume(self, execution: Execution) -> Execution:
        """Resume from last checkpoint without duplicating completed steps."""
        if execution.status not in ("awaiting_approval", "failed", "cancelled", "queued"):
            return execution
        # Reload plan
        from ..schemas.schemas import PlanStep, ExecutionPlan as EP
        plan_row = self.db.query(ExecutionPlan).filter_by(execution_id=execution.id).order_by(ExecutionPlan.created_at.desc()).first()
        if not plan_row: return execution
        steps = [PlanStep(**s) for s in plan_row.steps]
        plan = EP(steps=steps, estimated_cost=plan_row.estimated_cost)
        execution.status = "running"; self.db.commit()
        executor = Executor(self.registry, self.db, self.hot_state)
        try:
            await run_sequential(executor, execution, plan)
            self._record_cost(execution)
        except ApprovalPending:
            execution.status = "awaiting_approval"; self.db.commit()
        return execution

    def cancel(self, execution: Execution):
        execution.status = "cancelled"; execution.finished_at = datetime.now(timezone.utc); self.db.commit()

    def _resolve_key(self, user_id: str, provider_name: str) -> tuple[str, str]:
        """Return (api_key, base_url). Never logs or returns the key elsewhere."""
        cred = (self.db.query(ApiCredential)
                .filter_by(user_id=user_id, provider=provider_name.lower())
                .order_by(ApiCredential.is_default.desc())
                .first())
        if cred:
            try:
                return decrypt_secret(cred.encrypted_key), cred.base_url or ""
            except Exception:
                log.warning("failed to decrypt credential for %s", provider_name)
                return "", ""
        env_keys = {"openai": settings.openai_api_key, "groq": settings.groq_api_key,
                    "anthropic": settings.anthropic_api_key, "google": settings.gemini_api_key,
                    "gemini": settings.gemini_api_key}
        return env_keys.get(provider_name.lower(), ""), ""

    def _checkpoint(self, execution: Execution, state: dict):
        try:
            self.db.add(ExecutionCheckpoint(execution_id=execution.id, state=state, step_idx=state.get("step_idx", 0)))
            self.db.commit()
        except Exception:
            self.db.rollback()

    def _record_cost(self, execution: Execution):
        try:
            self.db.add(CostRecord(execution_id=execution.id, user_id=execution.user_id, provider=execution.provider,
                                   model=execution.model, total_tokens=execution.total_tokens or 0,
                                   cost=execution.total_cost or 0.0, estimated=False))
            self.db.commit()
        except Exception:
            self.db.rollback()
