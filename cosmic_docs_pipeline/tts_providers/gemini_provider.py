"""Gemini TTS provider — free online (quota-limited).

Uses `google-genai` with the TTS preview model. Default voice: Charon
(informative tone, closest to Quera's narrator).
"""

from __future__ import annotations

import base64
import logging
import wave
from pathlib import Path

logger = logging.getLogger("cosmic_docs.tts.gemini")


def _pcm_to_wav(pcm_bytes: bytes, out_path: Path, sample_rate: int = 24000) -> Path:
    """Wrap 16-bit PCM bytes in a WAV container."""
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(out_path), "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        wf.writeframes(pcm_bytes)
    return out_path


class GeminiTTSProvider:
    id = "gemini"

    def __init__(self) -> None:
        import config

        if not config.GEMINI_API_KEY:
            raise RuntimeError("GEMINI_API_KEY is not set")
        self._api_key = config.GEMINI_API_KEY
        self._model = config.GEMINI_TTS_MODEL
        self._default_voice = config.GEMINI_TTS_DEFAULT_VOICE

    def synthesize(
        self,
        text: str,
        out_path: str | Path,
        *,
        voice: str | None = None,
        reference_wav: str | Path | None = None,
        language: str = "hi",
    ) -> Path:
        if not text.strip():
            raise ValueError("Gemini TTS: empty text")

        from google import genai
        from google.genai import types

        out = Path(out_path)
        pick_voice = voice or self._default_voice

        client = genai.Client(api_key=self._api_key)
        logger.info(
            "Gemini TTS voice=%s model=%s chars=%d → %s",
            pick_voice, self._model, len(text), out.name,
        )

        response = client.models.generate_content(
            model=self._model,
            contents=text,
            config=types.GenerateContentConfig(
                response_modalities=["AUDIO"],
                speech_config=types.SpeechConfig(
                    voice_config=types.VoiceConfig(
                        prebuilt_voice_config=types.PrebuiltVoiceConfig(
                            voice_name=pick_voice,
                        ),
                    ),
                ),
            ),
        )

        # Extract inline audio data from the first candidate.
        audio_bytes: bytes | None = None
        try:
            for part in response.candidates[0].content.parts:
                inline = getattr(part, "inline_data", None)
                if inline and getattr(inline, "data", None):
                    raw = inline.data
                    audio_bytes = raw if isinstance(raw, bytes) else base64.b64decode(raw)
                    break
        except Exception as exc:
            raise RuntimeError(f"Gemini TTS response parse failed: {exc}") from exc

        if not audio_bytes:
            raise RuntimeError("Gemini TTS returned no audio bytes")

        return _pcm_to_wav(audio_bytes, out, sample_rate=24000)
