"""Google Veo 3.1 video provider — 4K native, 8 s clips via Gemini API."""

from __future__ import annotations

import logging
import time
from pathlib import Path

from .base import VideoProvider

logger = logging.getLogger("cosmic_docs.video.veo")


class VeoProvider(VideoProvider):
    id = "veo"
    MAX_CLIP_SEC = 8

    def __init__(self) -> None:
        import config

        if not config.GEMINI_API_KEY:
            raise RuntimeError("GEMINI_API_KEY is not set")
        self._api_key = config.GEMINI_API_KEY
        self._model = config.VEO_MODEL

    def generate(self, prompt: str, duration: float, out_path: str | Path) -> Path:
        out = Path(out_path)
        out.parent.mkdir(parents=True, exist_ok=True)

        try:
            from google import genai
        except ImportError as exc:
            raise RuntimeError("google-genai not installed") from exc

        client = genai.Client(api_key=self._api_key)
        logger.info("Veo submit model=%s target=%.1fs → %s", self._model, duration, out.name)

        operation = client.models.generate_videos(
            model=self._model,
            prompt=prompt,
        )

        # Poll until done
        while not getattr(operation, "done", False):
            time.sleep(5)
            operation = client.operations.get(operation)

        response = getattr(operation, "response", None) or {}
        videos = getattr(response, "generated_videos", None) or response.get("generated_videos", [])
        if not videos:
            raise RuntimeError(f"Veo returned no videos: {response}")

        video = videos[0]
        client.files.download(file=video.video)
        video.video.save(str(out))
        return out
