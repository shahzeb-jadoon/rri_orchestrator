"""Thin LiteLLM wrapper.

Kept tiny and side-effect-free so tests can monkeypatch `call_llm` with a fake
and run the whole graph offline (no API key, no network).
"""

from __future__ import annotations

from typing import Callable

# Type alias: a function that takes (messages, model) and returns a string.
LLMFn = Callable[[list[dict], str], str]


def call_llm(messages: list[dict], model: str = "gpt-4o-mini") -> str:
    """Single-shot completion via LiteLLM (provider-agnostic).

    LiteLLM gives us OpenAI / Gemini / Anthropic behind one interface, matching
    the routing approach already used in rri_orchestrator.
    """
    from litellm import completion  # imported lazily so the dep is optional in tests

    resp = completion(model=model, messages=messages)
    return resp["choices"][0]["message"]["content"]
