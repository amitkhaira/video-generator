"""Anthropic Claude LLM provider."""

from __future__ import annotations

import logging
import time

from .base import LLMResponse

logger = logging.getLogger("cosmic_docs.llm.claude")


class ClaudeProvider:
    id = "claude"

    def __init__(self) -> None:
        import config

        self._api_key = config.ANTHROPIC_API_KEY
        self._model = config.CLAUDE_MODEL

    def generate(
        self,
        *,
        system: str,
        user: str,
        max_output_tokens: int = 8192,
        temperature: float = 0.8,
    ) -> LLMResponse:
        if not self._api_key:
            raise RuntimeError("ANTHROPIC_API_KEY is not set")

        import anthropic

        client = anthropic.Anthropic(api_key=self._api_key)
        last_exc: Exception | None = None

        for attempt in range(1, 4):
            try:
                logger.info("Claude %s attempt %d", self._model, attempt)
                message = client.messages.create(
                    model=self._model,
                    system=system,
                    messages=[{"role": "user", "content": user}],
                    max_tokens=max_output_tokens,
                    temperature=temperature,
                )
                parts = []
                for block in message.content:
                    if getattr(block, "type", None) == "text":
                        parts.append(block.text)
                text = "".join(parts).strip()
                if not text:
                    raise RuntimeError("Empty response from Claude")
                return LLMResponse(text=text, provider=self.id, model=self._model)
            except Exception as exc:
                last_exc = exc
                logger.warning("Claude attempt %d failed: %s", attempt, exc)
                if attempt < 3:
                    time.sleep(15 * attempt)

        raise RuntimeError(f"Claude failed: {last_exc}") from last_exc
