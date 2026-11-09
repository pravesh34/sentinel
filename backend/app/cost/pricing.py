"""Versioned pricing table — rates live here/config, never hardcoded in tracker logic."""
# USD per 1k tokens. effective 2026-01, version 2026-01. Update via DB rows in prod.
PRICING: dict[tuple[str, str], tuple[float, float]] = {
    ("mock", "mock-llm-1"): (0.0, 0.0),
    ("openai", "gpt-4o-mini"): (0.00015, 0.0006),
    ("openai", "gpt-4o"): (0.0025, 0.01),
    ("google", "gemini-1.5-flash"): (0.000075, 0.0003),
    ("google", "gemini-1.5-pro"): (0.00125, 0.005),
    ("groq", "llama-3.1-8b-instant"): (0.00005, 0.00008),
    ("anthropic", "claude-3-5-sonnet"): (0.003, 0.015),
}
PRICING_VERSION = "2026-01"

def lookup(provider: str, model: str) -> tuple[float, float]:
    return PRICING.get((provider, model), (0.0, 0.0))

def cost_for(provider: str, model: str, input_tokens: int, output_tokens: int) -> float:
    i, o = lookup(provider, model)
    return (input_tokens / 1000) * i + (output_tokens / 1000) * o
