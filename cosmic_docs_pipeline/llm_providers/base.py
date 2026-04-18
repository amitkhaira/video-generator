"""Abstract LLM provider contract.

Every concrete provider (gemini / openai / claude) must subclass LLMProvider
and implement `generate`. The factory in __init__.py returns a provider
instance by name.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol, runtime_checkable


@dataclass
class LLMResponse:
    """Normalized response across providers."""

    text: str
    provider: str
    model: str


@runtime_checkable
class LLMProvider(Protocol):
    """Protocol implemented by every concrete LLM provider."""

    id: str

    def generate(
        self,
        *,
        system: str,
        user: str,
        max_output_tokens: int = 8192,
        temperature: float = 0.8,
    ) -> LLMResponse: ...
