"""Gemini LLM provider."""

from __future__ import annotations

import logging
import time

from .base import LLMResponse

logger = logging.getLogger("cosmic_docs.llm.gemini")

_MODEL_FALLBACKS = (
    "gemini-2.5-pro",
    "gemini-2.5-flash",
    "gemini-2.0-flash",
)


class GeminiProvider:
    id = "gemini"

    def __init__(self) -> None:
        import config

        self._api_key = config.GEMINI_API_KEY
        self._primary_model = config.GEMINI_MODEL

    def generate(
        self,
        *,
        system: str,
        user: str,
        max_output_tokens: int = 8192,
        temperature: float = 0.8,
    ) -> LLMResponse:
        if not self._api_key:
            raise RuntimeError("GEMINI_API_KEY is not set")

        from google import genai
        from google.genai import types

        client = genai.Client(api_key=self._api_key)
        candidates = [self._primary_model] + [
            m for m in _MODEL_FALLBACKS if m != self._primary_model
        ]

        last_exc: Exception | None = None
        for model_name in candidates:
            for attempt in range(1, 4):
                try:
                    logger.info("Gemini %s attempt %d", model_name, attempt)
                    response = client.models.generate_content(
                        model=model_name,
                        contents=user,
                        config=types.GenerateContentConfig(
                            temperature=temperature,
                            max_output_tokens=max_output_tokens,
                            system_instruction=system,
                        ),
                    )
                    text = (response.text or "").strip()
                    if not text:
                        raise RuntimeError("Empty response from Gemini")
                    return LLMResponse(text=text, provider=self.id, model=model_name)
                except Exception as exc:
                    last_exc = exc
                    logger.warning(
                        "Gemini %s attempt %d failed: %s", model_name, attempt, exc
                    )
                    if attempt < 3:
                        time.sleep(15 * attempt)

        raise RuntimeError(f"Gemini failed: {last_exc}") from last_exc
