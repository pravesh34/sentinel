"""SQLAlchemy entities — see docs/DATABASE.md. Works on SQLite & PostgreSQL."""
import uuid
from datetime import datetime, timezone
from sqlalchemy import (Column, String, Text, Float, Integer, DateTime, JSON, ForeignKey, Boolean, Index)
from sqlalchemy.orm import relationship
from ..database.session import Base

def _uuid(): return str(uuid.uuid4())
def _now(): return datetime.now(timezone.utc)

class User(Base):
    __tablename__ = "users"
    id = Column(String, primary_key=True, default=_uuid)
    email = Column(String, unique=True, nullable=False, index=True)
    hashed_password = Column(String, nullable=False)
    plan = Column(String, default="free")
    created_at = Column(DateTime, default=_now)

class ApiCredential(Base):
    __tablename__ = "api_credentials"
    id = Column(String, primary_key=True, default=_uuid)
    user_id = Column(String, ForeignKey("users.id"), nullable=False, index=True)
    provider = Column(String, nullable=False)
    encrypted_key = Column(Text, nullable=False)  # Fernet ciphertext only
    base_url = Column(String, default="")
    is_default = Column(Boolean, default=False)

class Execution(Base):
    __tablename__ = "executions"
    id = Column(String, primary_key=True, default=_uuid)
    user_id = Column(String, ForeignKey("users.id"), nullable=False, index=True)
    objective = Column(Text, nullable=False)
    status = Column(String, default="queued", index=True)  # queued|running|awaiting_approval|completed|failed|cancelled|budget_exceeded|limit_exceeded
    mode = Column(String, default="supervised")  # manual|supervised|autonomous
    complexity = Column(String, default="medium")
    max_steps = Column(Integer, default=20)
    max_tool_calls = Column(Integer, default=30)
    max_cost = Column(Float, default=1.0)
    max_runtime_s = Column(Integer, default=300)
    max_tokens = Column(Integer, default=20000)
    allowed_tools = Column(JSON, default=list)
    provider = Column(String, default="mock")
    model = Column(String, default="mock-llm-1")
    total_cost = Column(Float, default=0.0)
    total_tokens = Column(Integer, default=0)
    correlation_id = Column(String, default="", index=True)
    result = Column(JSON, nullable=True)
    error = Column(Text, nullable=True)
    created_at = Column(DateTime, default=_now)
    started_at = Column(DateTime, nullable=True)
    finished_at = Column(DateTime, nullable=True)
    steps = relationship("ExecutionStep", back_populates="execution", cascade="all, delete-orphan")

class ExecutionPlan(Base):
    __tablename__ = "execution_plans"
    id = Column(String, primary_key=True, default=_uuid)
    execution_id = Column(String, ForeignKey("executions.id"), nullable=False, index=True)
    steps = Column(JSON, default=list)
    estimated_cost = Column(Float, default=0.0)
    created_at = Column(DateTime, default=_now)

class ExecutionStep(Base):
    __tablename__ = "execution_steps"
    __table_args__ = (Index("ix_steps_exec", "execution_id"),)
    id = Column(String, primary_key=True, default=_uuid)
    execution_id = Column(String, ForeignKey("executions.id"), nullable=False)
    step_id = Column(String, nullable=False)
    description = Column(Text, default="")
    tool_id = Column(String, default="")
    status = Column(String, default="pending")  # pending|running|completed|failed|waiting_approval|skipped
    args = Column(JSON, default=dict)
    result = Column(JSON, nullable=True)
    estimated_cost = Column(Float, default=0.0)
    actual_cost = Column(Float, default=0.0)
    risk_level = Column(String, default="LOW")
    retries = Column(Integer, default=0)
    error = Column(Text, nullable=True)
    created_at = Column(DateTime, default=_now)
    started_at = Column(DateTime, nullable=True)
    finished_at = Column(DateTime, nullable=True)
    execution = relationship("Execution", back_populates="steps")

class ToolRegistryRow(Base):
    __tablename__ = "tool_registry"
    tool_id = Column(String, primary_key=True)
    name = Column(String, nullable=False)
    description = Column(Text, default="")
    input_schema = Column(JSON, default=dict)
    risk_level = Column(String, default="LOW")
    enabled = Column(Boolean, default=True)
    timeout_s = Column(Integer, default=30)
    max_retries = Column(Integer, default=2)

class ToolInvocation(Base):
    __tablename__ = "tool_invocations"
    id = Column(String, primary_key=True, default=_uuid)
    execution_id = Column(String, ForeignKey("executions.id"), nullable=False, index=True)
    step_id = Column(String, default="")
    tool_id = Column(String, nullable=False)
    idempotency_key = Column(String, unique=True, nullable=False, index=True)
    args = Column(JSON, default=dict)
    result = Column(JSON, nullable=True)
    status = Column(String, default="running")
    duration_ms = Column(Integer, default=0)
    cost = Column(Float, default=0.0)
    created_at = Column(DateTime, default=_now)

class CostRecord(Base):
    __tablename__ = "cost_records"
    id = Column(String, primary_key=True, default=_uuid)
    execution_id = Column(String, ForeignKey("executions.id"), nullable=True, index=True)
    user_id = Column(String, ForeignKey("users.id"), nullable=True, index=True)
    provider = Column(String, default="mock")
    model = Column(String, default="mock-llm-1")
    input_tokens = Column(Integer, default=0)
    output_tokens = Column(Integer, default=0)
    total_tokens = Column(Integer, default=0)
    cost = Column(Float, default=0.0)
    estimated = Column(Boolean, default=False)
    created_at = Column(DateTime, default=_now)

class BudgetLimit(Base):
    __tablename__ = "budget_limits"
    id = Column(String, primary_key=True, default=_uuid)
    user_id = Column(String, ForeignKey("users.id"), nullable=False, index=True)
    scope = Column(String, default="execution")  # execution|daily|monthly
    max_cost = Column(Float, default=10.0)
    max_tokens = Column(Integer, default=100000)

class ExecutionCheckpoint(Base):
    __tablename__ = "execution_checkpoints"
    id = Column(String, primary_key=True, default=_uuid)
    execution_id = Column(String, ForeignKey("executions.id"), nullable=False, index=True)
    state = Column(JSON, default=dict)
    step_idx = Column(Integer, default=0)
    created_at = Column(DateTime, default=_now)

class ApprovalRequest(Base):
    __tablename__ = "approval_requests"
    id = Column(String, primary_key=True, default=_uuid)
    execution_id = Column(String, ForeignKey("executions.id"), nullable=False, index=True)
    step_id = Column(String, default="")
    tool_id = Column(String, default="")
    action_hash = Column(String, nullable=False)
    args = Column(JSON, default=dict)
    risk_level = Column(String, default="HIGH")
    status = Column(String, default="pending")  # pending|approved|rejected|expired
    reason = Column(Text, default="")
    expires_at = Column(DateTime, nullable=True)
    decided_at = Column(DateTime, nullable=True)

class AuditLog(Base):
    __tablename__ = "audit_logs"
    id = Column(String, primary_key=True, default=_uuid)
    execution_id = Column(String, nullable=True, index=True)
    actor = Column(String, default="system")
    action = Column(String, nullable=False)
    detail = Column(JSON, default=dict)
    correlation_id = Column(String, default="")
    created_at = Column(DateTime, default=_now)

class ProviderPricing(Base):
    __tablename__ = "provider_pricing"
    provider = Column(String, primary_key=True)
    model = Column(String, primary_key=True)
    version = Column(String, primary_key=True, default="2026-01")
    input_per_1k = Column(Float, default=0.0)
    output_per_1k = Column(Float, default=0.0)
    effective_date = Column(String, default="2026-01-01")

class ExecutionError(Base):
    __tablename__ = "execution_errors"
    id = Column(String, primary_key=True, default=_uuid)
    execution_id = Column(String, ForeignKey("executions.id"), nullable=True, index=True)
    step_id = Column(String, default="")
    error_type = Column(String, default="error")
    message = Column(Text, default="")
    retryable = Column(Boolean, default=False)
    created_at = Column(DateTime, default=_now)
