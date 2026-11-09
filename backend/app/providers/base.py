"""Provider abstraction. MockLLM is deterministic for tests; real adapters use httpx."""
import hashlib
from abc import ABC, abstractmethod
from dataclasses import dataclass

@dataclass
class LLMResult:
    text: str
    input_tokens: int
    output_tokens: int
    provider: str
    model: str

class LLMProvider(ABC):
    name: str = "base"
    @abstractmethod
    def chat(self, messages: list[dict], model: str = "") -> LLMResult: ...

class MockLLM(LLMProvider):
    name = "mock"
    def chat(self, messages: list[dict], model: str = "mock-llm-1") -> LLMResult:
        prompt = " ".join(m.get("content", "") for m in messages)
        # Deterministic pseudo-tokens from prompt hash
        h = int(hashlib.sha256(prompt.encode()).hexdigest()[:8], 16)
        input_tokens = max(1, len(prompt) // 4)
        output_tokens = 20 + (h % 40)  # 20-59, capped by budget tests via limits
        # If prompt asks for plan JSON, return structured-ish text planner can parse
        if "plan" in prompt.lower() or "steps" in prompt.lower():
            text = '{"steps":[{"step_id":"s1","description":"Search web","selected_tool":"web_search","expected_output":"sources","estimated_cost":0.0,"risk_level":"MEDIUM","args":{"query":"agentic AI"}},{"step_id":"s2","description":"Summarize","selected_tool":"summarizer","expected_output":"summary","estimated_cost":0.0,"risk_level":"LOW","args":{"text":"see s1"}}]}'
        elif "hello" in prompt.lower() or "hi" == prompt.strip().lower():
            text = "Hello from MockLLM."
        else:
            text = f"MockLLM response ({input_tokens} in tokens). Task processed."
        return LLMResult(text=text, input_tokens=input_tokens, output_tokens=output_tokens, provider="mock", model=model or "mock-llm-1")

class HTTPProvider(LLMProvider):
    """Generic OpenAI-compatible HTTP provider (OpenAI/Groq/compatible)."""
    name = "openai-compatible"
    def __init__(self, base_url: str, api_key: str):
        self.base_url = base_url.rstrip("/"); self.api_key = api_key
    def chat(self, messages: list[dict], model: str = "") -> LLMResult:
        import httpx
        resp = httpx.post(f"{self.base_url}/chat/completions",
                          headers={"Authorization": f"Bearer {self.api_key}"},
                          json={"model": model, "messages": messages, "temperature": 0}, timeout=60)
        resp.raise_for_status()
        data = resp.json()
        text = data["choices"][0]["message"]["content"]
        usage = data.get("usage", {})
        return LLMResult(text=text, input_tokens=usage.get("prompt_tokens", 0),
                         output_tokens=usage.get("completion_tokens", 0), provider=self.name, model=model)

def get_provider(name: str, api_key: str = "", base_url: str = "") -> LLMProvider:
    name = (name or "mock").lower()
    if name == "mock": return MockLLM()
    openai_bases = {"openai": "https://api.openai.com/v1", "groq": "https://api.groq.com/openai/v1",
                    "anthropic": "https://api.openai.com/v1", "google": "https://generativelanguage.googleapis.com/v1"}
    return HTTPProvider(base_url or openai_bases.get(name, "https://api.openai.com/v1"), api_key)

def get_provider_with_fallback(primary: str, fallback: str = "", api_key: str = "", base_url: str = ""):
    """Return list of providers to try in order."""
    providers = [get_provider(primary, api_key, base_url)]
    if fallback and fallback != primary:
        providers.append(get_provider(fallback))
    return providers
