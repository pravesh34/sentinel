"""Planning agent: LLM → validated Pydantic plan. Never executes code/tools itself."""
import json
from ..providers.base import LLMProvider, MockLLM
from ..schemas.schemas import ExecutionPlan, PlanStep
from ..tools.registry import ToolRegistry

class Planner:
    def __init__(self, provider: LLMProvider | None = None, registry: ToolRegistry | None = None):
        self.provider = provider or MockLLM()
        self.registry = registry

    def plan(self, objective: str, model: str = "mock-llm-1", allowed_tools: list[str] | None = None) -> ExecutionPlan:
        messages = [
            {"role": "system", "content": "You are SENTINEL planner. Output JSON plan with steps. Use only listed tools."},
            {"role": "user", "content": f"Objective: {objective}\nOutput JSON: {{\"steps\":[...]}} with fields step_id, description, selected_tool, expected_output, estimated_cost, risk_level, args."},
        ]
        result = self.provider.chat(messages, model=model)
        plan = self._parse(result.text, objective)
        # Validate against registry: unknown tools → drop/replace with calculator? Fail closed: raise.
        if self.registry:
            valid_ids = {t.tool_id for t in self.registry.list_tools()}
            for s in plan.steps:
                if s.selected_tool and s.selected_tool not in valid_ids:
                    raise ValueError(f"planner selected unknown tool: {s.selected_tool}")
        return plan

    def _parse(self, text: str, objective: str) -> ExecutionPlan:
        try:
            data = json.loads(text[text.find("{"):text.rfind("}")+1])
            steps = [PlanStep(**{**s, "dependencies": s.get("dependencies", [])}) for s in data.get("steps", [])]
            if not steps: raise ValueError("empty plan")
            return ExecutionPlan(steps=steps, estimated_cost=sum(s.estimated_cost for s in steps), complexity="medium")
        except Exception:
            # Deterministic fallback plan (still validated downstream)
            kw = objective.lower()
            if "calculate" in kw or "math" in kw:
                return ExecutionPlan(steps=[PlanStep(step_id="s1", description="Calculate", selected_tool="calculator",
                                                     expected_output="value", args={"expression": "2+2"})])
            if "summar" in kw:
                return ExecutionPlan(steps=[PlanStep(step_id="s1", description="Summarize", selected_tool="summarizer",
                                                     expected_output="summary", args={"text": objective})])
            return ExecutionPlan(steps=[
                PlanStep(step_id="s1", description=f"Research: {objective[:80]}", selected_tool="web_search", expected_output="sources",
                         risk_level="MEDIUM", args={"query": objective[:120]}),
                PlanStep(step_id="s2", description="Summarize findings", selected_tool="summarizer", expected_output="summary",
                         dependencies=["s1"], args={"text": "Research findings for: " + objective[:120]}),
            ])
