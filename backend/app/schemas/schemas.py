from typing import Any, Literal, Optional
from pydantic import BaseModel, Field, field_validator

RiskLevel = Literal["LOW", "MEDIUM", "HIGH", "CRITICAL"]
ExecMode = Literal["manual", "supervised", "autonomous"]

class RegisterIn(BaseModel):
    email: str
    password: str = Field(min_length=8)
    @field_validator("email")
    @classmethod
    def _email(cls, v): return v.strip().lower()

class LoginIn(BaseModel):
    email: str; password: str

class TokenOut(BaseModel):
    access_token: str; token_type: str = "bearer"

class UserOut(BaseModel):
    id: str; email: str; plan: str = "free"

class CreateExecutionIn(BaseModel):
    objective: str = Field(min_length=3, max_length=4000)
    mode: ExecMode = "supervised"
    max_steps: int = Field(default=20, ge=1, le=100)
    max_tool_calls: int = Field(default=30, ge=1, le=200)
    max_cost: float = Field(default=1.0, gt=0)
    max_runtime_s: int = Field(default=300, ge=5, le=3600)
    max_tokens: int = Field(default=20000, ge=100, le=500000)
    allowed_tools: list[str] = Field(default_factory=list)  # empty = all enabled non-CRITICAL
    provider: str = "mock"
    model: str = "mock-llm-1"

class PlanStep(BaseModel):
    step_id: str
    description: str
    dependencies: list[str] = Field(default_factory=list)
    selected_tool: str = ""
    expected_output: str = ""
    estimated_cost: float = 0.0
    risk_level: RiskLevel = "LOW"
    timeout: int = 30
    retry_policy: dict[str, Any] = Field(default_factory=lambda: {"max_retries": 2})
    args: dict[str, Any] = Field(default_factory=dict)

class ExecutionPlan(BaseModel):
    steps: list[PlanStep]
    estimated_cost: float = 0.0
    complexity: str = "medium"

class ExecutionOut(BaseModel):
    id: str; objective: str; status: str; mode: str
    total_cost: float; total_tokens: int; correlation_id: str
    result: Optional[dict[str, Any]] = None; error: Optional[str] = None

class ApprovalOut(BaseModel):
    id: str; execution_id: str; step_id: str; tool_id: str
    risk_level: str; status: str; args: dict[str, Any]

class ToolOut(BaseModel):
    tool_id: str; name: str; description: str; risk_level: str; enabled: bool; timeout_s: int

class ToolPermIn(BaseModel):
    enabled: Optional[bool] = None
    timeout_s: Optional[int] = None

class BudgetIn(BaseModel):
    scope: str = "execution"; max_cost: float = 10.0; max_tokens: int = 100000

class BudgetOut(BudgetIn):
    id: str

class CredentialIn(BaseModel):
    provider: str; api_key: str; base_url: str = ""; is_default: bool = False

class ApprovalDecision(BaseModel):
    # Approval is bound to exact action_hash server-side; client only sends decision.
    decision: Literal["approve", "reject"]
