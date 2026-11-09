"""Planning agent: LLM → validated Pydantic plan. Never executes code/tools itself."""
import json
from ..providers.base import LLMProvider, MockLLM
from ..schemas.schemas import ExecutionPlan, PlanStep
from ..tools.registry import ToolRegistry

class Planner:
    def __init__(self, provider: LLMProvider | None = None, registry: ToolRegistry | None = None):
        self.provider = provider or MockLLM()
        self.registry = registry
        self.last_result = None  # LLMResult of the planning call (for cost accounting)

    def plan(self, objective: str, model: str = "mock-llm-1", allowed_tools: list[str] | None = None) -> ExecutionPlan:
        tool_ids = [t.tool_id for t in self.registry.list_tools()] if self.registry else ["web_search", "summarizer"]
        if allowed_tools:
            tool_ids = [t for t in tool_ids if t in allowed_tools] or tool_ids
        messages = [
            {"role": "system", "content": "You are SENTINEL planner. Reply with ONLY a JSON object (no markdown, no prose). Use only these tools: " + ", ".join(tool_ids) + ". Each step MUST have: step_id (string s1,s2...), description (string), selected_tool (one of the above), expected_output (string), estimated_cost (number), risk_level (LOW|MEDIUM|HIGH|CRITICAL), args (object). Valid args: calculator={expression}, web_search={query}, summarizer={text}, json_parser={text}, file_reader={path}, file_writer={path,content}, doc_generator={title,sections}, http_request={url,method}, db_query={sql}, python_sandbox={code}."},
            {"role": "user", "content": f"Objective: {objective}\nReply ONLY with JSON like: {{\"steps\":[{{\"step_id\":\"s1\",\"description\":\"...\",\"selected_tool\":\"web_search\",\"expected_output\":\"sources\",\"estimated_cost\":0.001,\"risk_level\":\"MEDIUM\",\"args\":{{\"query\":\"...\"}}}}, ...]}}"},
        ]
        result = self.provider.chat(messages, model=model)
        self.last_result = result  # include LLM token/cost usage in run accounting
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
            cleaned = text.strip()
            # Strip markdown code fences if present
            if cleaned.startswith("```"):
                cleaned = cleaned.split("```", 2)[1] if cleaned.count("```") >= 2 else cleaned.strip("`")
                cleaned = cleaned.replace("json", "", 1).strip() if cleaned.startswith("json") else cleaned
            start, end = cleaned.find("{"), cleaned.rfind("}")
            if start == -1 or end == -1:
                raise ValueError("no JSON object in planner output")
            data = json.loads(cleaned[start:end + 1])
            raw_steps = data.get("steps", [])
            if not raw_steps: raise ValueError("empty plan")
            steps = []
            for i, s in enumerate(raw_steps):
                norm = {
                    "step_id": str(s.get("step_id") or s.get("id") or f"s{i+1}"),
                    "description": str(s.get("description") or s.get("title") or f"Step {i+1}"),
                    "selected_tool": str(s.get("selected_tool") or s.get("tool") or s.get("tool_id") or ""),
                    "expected_output": str(s.get("expected_output") or ""),
                    "estimated_cost": float(s.get("estimated_cost") or 0.0),
                    "risk_level": s.get("risk_level") if s.get("risk_level") in ("LOW", "MEDIUM", "HIGH", "CRITICAL") else "LOW",
                    "args": s.get("args") if isinstance(s.get("args"), dict) else {},
                    "dependencies": s.get("dependencies") if isinstance(s.get("dependencies"), list) else [],
                }
                steps.append(PlanStep(**norm))
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
