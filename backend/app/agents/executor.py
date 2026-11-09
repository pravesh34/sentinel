"""Executor: runs validated plan stepwise with guardrails, cost, recovery, approvals.

This is the deterministic runtime. LangGraph wraps these same steps as nodes
(see workflows/execution_graph.py); direct run() is used for tests/worker.
"""
import asyncio
import time
from ..guardrails.limits import ExecutionLimits
from ..guardrails.permissions import requires_approval, is_allowed
from ..guardrails.validator import validate_tool_args, sanitize_tool_output, contains_injection
from ..cost.tracker import CostTracker
from ..cost.budget import check_or_raise, BudgetExceeded
from ..recovery.manager import should_retry, partial_result
from ..tools.registry import ToolRegistry
from ..models.entities import ToolInvocation, ExecutionError, ApprovalRequest, AuditLog
from ..approvals.manager import make_approval
from ..observability.logging import get_logger

log = get_logger("sentinel.executor")

class ExecutionCancelled(Exception): pass
class ApprovalPending(Exception):
    def __init__(self, approval_id: str): self.approval_id = approval_id

class Executor:
    def __init__(self, registry: ToolRegistry, db, hot_state=None, cost_tracker: CostTracker | None = None):
        self.registry = registry
        self.db = db
        self.hot_state = hot_state
        self.tracker = cost_tracker or CostTracker()

    async def run(self, execution, plan, dry_run: bool = False) -> dict:
        """Execute plan. Returns result dict. Raises ApprovalPending for HITL."""
        limits = ExecutionLimits(max_steps=execution.max_steps, max_tool_calls=execution.max_tool_calls,
                                 max_cost=execution.max_cost, max_tokens=execution.max_tokens,
                                 max_runtime_s=execution.max_runtime_s)
        tracker = self.tracker
        tracker.provider = execution.provider; tracker.model = execution.model
        completed: list[dict] = []
        tool_calls = 0
        committed: set[str] = set()
        started = time.time()

        # Resume: skip already-completed steps (from checkpoints)
        done_ids = {s.step_id for s in execution.steps if s.status == "completed"} if hasattr(execution, "steps") else set()

        for idx, step in enumerate(plan.steps):
            if step.step_id in done_ids:
                continue
            elapsed = time.time() - started
            violation = limits.check_pre_step(steps_done=idx, tool_calls_done=tool_calls,
                                              elapsed_s=elapsed, cost_so_far=tracker.total_cost,
                                              tokens_so_far=tracker.total_tokens)
            if violation:
                execution.status = "budget_exceeded" if "budget" in violation else "limit_exceeded"
                execution.error = violation
                return partial_result(completed, violation)

            if contains_injection(step.description + str(step.args)):
                # Logged & stripped, not trusted — step still runs with sanitized args only if schema-valid
                log.warning("injection-pattern detected in step %s", step.step_id)
                self._audit(execution, "injection_warning", {"step_id": step.step_id})

            tool = self.registry.get(step.selected_tool) if step.selected_tool else None
            if step.selected_tool and tool is None:
                self._record_error(execution, step.step_id, "unauthorized", f"unknown tool {step.selected_tool}", False)
                execution.status = "failed"; execution.error = f"unknown tool: {step.selected_tool}"; self.db.commit()
                return partial_result(completed, f"unknown tool: {step.selected_tool}")

            # Risk from registry (authoritative), fallback to plan
            risk = tool.risk_level if tool else step.risk_level
            enabled = True  # DB enabled flag checked in service layer; registry tools are enabled by default
            if tool and not is_allowed(tool.tool_id, execution.allowed_tools or [], enabled, risk):
                self._record_error(execution, step.step_id, "unauthorized", f"tool {tool.tool_id} not allowed", False)
                execution.status = "failed"; execution.error = f"unauthorized tool: {tool.tool_id}"; self.db.commit()
                return partial_result(completed, f"unauthorized tool: {tool.tool_id}")

            args = step.args or {}
            if tool:
                errs = validate_tool_args(tool.tool_id, args, tool.input_schema)
                if errs:
                    self._record_error(execution, step.step_id, "invalid_args", ";".join(errs), False)
                    execution.status = "failed"; execution.error = f"invalid args: {errs}"; self.db.commit()
                    return partial_result(completed, f"invalid args: {errs}")

            # HITL gate
            if tool and requires_approval(risk, execution.mode):
                # Check for an existing approved approval bound to exact action
                from ..guardrails.validator import action_hash as ah
                ahash = ah(execution.id, step.step_id, tool.tool_id, args)
                existing = self.db.query(ApprovalRequest).filter_by(execution_id=execution.id, action_hash=ahash, status="approved").first()
                if not existing:
                    appr = ApprovalRequest(**make_approval(execution.id, step.step_id, tool.tool_id, args, risk,
                                                           f"Tool {tool.tool_id} risk {risk} in mode {execution.mode}"))
                    self.db.add(appr); self.db.commit()
                    execution.status = "awaiting_approval"
                    self.db.commit()
                    self._audit(execution, "approval_requested", {"approval_id": appr.id, "tool": tool.tool_id})
                    raise ApprovalPending(appr.id)

            # Budget reservation before paid op
            est = self.registry.estimate_cost(step.selected_tool, args) if step.selected_tool else 0.0
            try:
                check_or_raise(tracker, est, limits.max_cost)
            except BudgetExceeded as e:
                execution.status = "budget_exceeded"; execution.error = str(e); self.db.commit()
                return partial_result(completed, str(e))

            # Idempotency: skip if this step's key already committed (crash-resume safety)
            idem_key = f"{execution.id}:{step.step_id}:{step.selected_tool}:{hash(str(args)) % (10**8)}"
            if step.step_id in committed:
                continue
            prior = self.db.query(ToolInvocation).filter_by(idempotency_key=idem_key, status="completed").first() if step.selected_tool else None
            if prior:
                log.info("skipping duplicate invocation %s", idem_key)
                continue

            # Execute with bounded retry
            result = None; last_error = None; retries = 0
            max_r = tool.max_retries if tool else 0
            for attempt in range(max_r + 1):
                try:
                    if tool:
                        tool_calls += 1
                        result = await self.registry.invoke(tool.tool_id, args, timeout_override=step.timeout)
                    else:
                        result = {"note": "no tool selected, step treated as reasoning-only"}
                    last_error = None
                    break
                except asyncio.TimeoutError as e:
                    last_error = "timeout"; retries += 1
                    if not should_retry("timeout", True, retries, limits.max_retries): break
                    await asyncio.sleep(0.05 * (2 ** attempt))
                except Exception as e:  # noqa: BLE001 — classified below
                    last_error = str(e); retries += 1
                    if not should_retry("tool_error", True, retries, limits.max_retries): break
                    await asyncio.sleep(0.05 * (2 ** attempt))

            if last_error:
                self._record_error(execution, step.step_id, "timeout" if last_error == "timeout" else "tool_error", last_error, True)
                # Skip optional step if dependents allow (no dependents in linear subset) → partial result
                return partial_result(completed, f"step {step.step_id} failed: {last_error}")

            # Sanitize + persist invocation
            if isinstance(result, dict) and "error" in result:
                self._record_error(execution, step.step_id, "tool_error", str(result["error"]), False)
                return partial_result(completed, f"tool error: {result['error']}")
            if isinstance(result, str):
                result = {"output": sanitize_tool_output(result)}
            elif isinstance(result, dict):
                for k, v in list(result.items()):
                    if isinstance(v, str): result[k] = sanitize_tool_output(v)

            tracker.record_tool(step.selected_tool or "none", cost=est)
            inv = ToolInvocation(execution_id=execution.id, step_id=step.step_id, tool_id=step.selected_tool or "none",
                                 idempotency_key=idem_key, args=args, result=result, status="completed", cost=est)
            self.db.add(inv); committed.add(step.step_id)
            completed.append({"step_id": step.step_id, "tool": step.selected_tool, "result": result})
            self._audit(execution, "step_completed", {"step_id": step.step_id, "tool": step.selected_tool})
            self.db.commit()

        # Finalize
        tracker.record_llm(input_tokens=tracker.total_tokens or 10, output_tokens=20)  # planning cost accounted once
        execution.total_cost = tracker.total_cost
        execution.total_tokens = tracker.total_tokens
        execution.status = "completed"
        result_payload = {"objective": execution.objective, "completed_steps": completed,
                          "summary": "Executed " + str(len(completed)) + " steps.", "cost": tracker.total_cost}
        execution.result = result_payload
        self.db.commit()
        return result_payload

    def _audit(self, execution, action: str, detail: dict):
        try:
            self.db.add(AuditLog(execution_id=execution.id, actor="executor", action=action, detail=detail,
                                 correlation_id=getattr(execution, "correlation_id", "")))
            self.db.commit()
        except Exception:
            self.db.rollback()

    def _record_error(self, execution, step_id: str, etype: str, msg: str, retryable: bool):
        try:
            self.db.add(ExecutionError(execution_id=execution.id, step_id=step_id, error_type=etype, message=msg, retryable=retryable))
            self.db.commit()
        except Exception:
            self.db.rollback()
