"""OpenAI (GPT-4o / GPT-5) LLM provider."""

from __future__ import annotations

import logging
import time

from .base import LLMResponse

logger = logging.getLogger("cosmic_docs.llm.openai")


class OpenAIProvider:
    id = "openai"

    def __init__(self) -> None:
        import config

        self._api_key = config.OPENAI_API_KEY
        self._model = config.OPENAI_MODEL

    def generate(
        self,
        *,
        system: str,
        user: str,
        max_output_tokens: int = 8192,
        temperature: float = 0.8,
    ) -> LLMResponse:
        if not self._api_key:
            raise RuntimeError("OPENAI_API_KEY is not set")

        from openai import OpenAI

        client = OpenAI(api_key=self._api_key)
        last_exc: Exception | None = None

        for attempt in range(1, 4):
            try:
                logger.info("OpenAI %s attempt %d", self._model, attempt)
                completion = client.chat.completions.create(
                    model=self._model,
                    messages=[
                        {"role": "system", "content": system},
                        {"role": "user", "content": user},
                    ],
                    temperature=temperature,
                    max_tokens=max_output_tokens,
                )
                text = (completion.choices[0].message.content or "").strip()
                if not text:
                    raise RuntimeError("Empty response from OpenAI")
                return LLMResponse(text=text, provider=self.id, model=self._model)
            except Exception as exc:
                last_exc = exc
                logger.warning("OpenAI attempt %d failed: %s", attempt, exc)
                if attempt < 3:
                    time.sleep(15 * attempt)

        raise RuntimeError(f"OpenAI failed: {last_exc}") from last_exc
