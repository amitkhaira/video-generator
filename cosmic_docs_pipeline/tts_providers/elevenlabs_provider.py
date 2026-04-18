"""ElevenLabs TTS provider — premium online, voice cloning."""

from __future__ import annotations

import logging
from pathlib import Path

logger = logging.getLogger("cosmic_docs.tts.elevenlabs")


class ElevenLabsProvider:
    id = "elevenlabs"

    def __init__(self) -> None:
        import config

        if not config.ELEVENLABS_API_KEY:
            raise RuntimeError("ELEVENLABS_API_KEY is not set")
        self._api_key = config.ELEVENLABS_API_KEY
        self._model = config.ELEVENLABS_MODEL

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
            raise ValueError("ElevenLabs: empty text")
        if not voice:
            raise RuntimeError(
                "ElevenLabs requires TTS_VOICE (paste a voice id from your dashboard)."
            )

        try:
            from elevenlabs.client import ElevenLabs
        except ImportError as exc:
            raise RuntimeError(
                "elevenlabs package not installed. pip install elevenlabs>=1.0.0"
            ) from exc

        out = Path(out_path)
        out.parent.mkdir(parents=True, exist_ok=True)

        client = ElevenLabs(api_key=self._api_key)
        logger.info(
            "ElevenLabs synthesize voice=%s model=%s chars=%d → %s",
            voice, self._model, len(text), out.name,
        )
        audio_stream = client.text_to_speech.convert(
            voice_id=voice,
            model_id=self._model,
            text=text,
            output_format="mp3_44100_128",
        )

        # Write MP3 first, then convert to WAV via ffmpeg for pipeline uniformity.
        tmp_mp3 = out.with_suffix(".mp3")
        with open(tmp_mp3, "wb") as fh:
            for chunk in audio_stream:
                fh.write(chunk)

        import subprocess

        import config

        subprocess.run(
            [
                config.FFMPEG_PATH,
                "-y",
                "-i", str(tmp_mp3),
                "-ar", "24000",
                "-ac", "1",
                str(out),
            ],
            check=True,
            capture_output=True,
        )
        try:
            tmp_mp3.unlink()
        except OSError:
            pass
        return out
