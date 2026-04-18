"""LLM provider factory for script + video prompt generation.

Mirrors the pattern already proven in documentary_pipeline/voice_prompt/providers/,
but isolated here so cosmic_docs_pipeline remains standalone.
"""

from __future__ import annotations

from .base import LLMProvider, LLMResponse

_REGISTRY: dict[str, str] = {
    "gemini": "gemini:GeminiProvider",
    "openai": "openai_chat:OpenAIProvider",
    "claude": "anthropic_claude:ClaudeProvider",
}


def get_provider(name: str) -> LLMProvider:
    key = (name or "").strip().lower()
    if key not in _REGISTRY:
        raise ValueError(
            f"Unknown LLM provider '{name}'. Allowed: {sorted(_REGISTRY)}"
        )

    module_part, class_part = _REGISTRY[key].split(":")
    import importlib

    module = importlib.import_module(f".{module_part}", package=__name__)
    cls = getattr(module, class_part)
    return cls()


__all__ = ["LLMProvider", "LLMResponse", "get_provider"]
