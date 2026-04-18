"""Meta AI video provider (free, 5 s clips) — default for cosmic_docs_pipeline.

Ports the cookie-authenticated metaai_api SDK flow from
documentary_pipeline/02_video_generator.py but simplified for the
audio-first architecture: one prompt + target duration → one MP4.

Meta AI caps at 5 s; `03_audio_timeline.py` handles scene-continuation
by splitting long beats into multiple sequential clips.
"""

from __future__ import annotations

import logging
import os
import time
from pathlib import Path

import requests

from .base import VideoProvider

logger = logging.getLogger("cosmic_docs.video.meta_ai")


class MetaAIVideoProvider(VideoProvider):
    id = "meta_ai"
    MAX_CLIP_SEC = 5

    def __init__(self) -> None:
        self._cookies = self._load_cookies()
        try:
            from metaai_api import MetaAI
        except ImportError as exc:
            raise RuntimeError(
                "metaai_api SDK not installed. See documentary_pipeline for install instructions."
            ) from exc
        self._ai = MetaAI(cookies=self._cookies)
        self._last_source_urls: list[str] = []

    @staticmethod
    def _load_cookies() -> dict[str, str]:
        import config

        cookies: dict[str, str] = {}
        required_map = {"datr": "META_AI_DATR", "ecto_1_sess": "META_AI_ECTO_1_SESS"}
        for key, env_var in required_map.items():
            val = os.getenv(env_var, "")
            if not val:
                raise RuntimeError(
                    f"Missing required Meta AI cookie: {env_var}. "
                    "Set it in .env."
                )
            cookies[key] = val

        for env_var in config.META_AI_COOKIES_OPTIONAL:
            key = env_var.replace("META_AI_", "").lower()
            val = os.getenv(env_var, "")
            if val:
                cookies[key] = val

        return cookies

    @staticmethod
    def _urls_from_generate_video_new(result: dict) -> list[str]:
        seen: set[str] = set()
        ordered: list[str] = []

        def add(u):
            if u and isinstance(u, str) and u.startswith("http") and u not in seen:
                seen.add(u)
                ordered.append(u)

        for u in result.get("video_urls") or []:
            add(u)
        for vid in result.get("video_objects") or []:
            if isinstance(vid, dict):
                for k in ("url", "fallbackUrl"):
                    add(vid.get(k))
        return ordered

    def generate(self, prompt: str, duration: float, out_path: str | Path) -> Path:
        import config

        out = Path(out_path)
        out.parent.mkdir(parents=True, exist_ok=True)

        # Meta AI does not honour an exact duration — it always returns a ~5 s clip.
        # We accept whatever it returns and the merge stage pads / trims as needed.
        logger.info(
            "Meta AI generate (target=%.2fs cap=%ds) → %s",
            duration, self.MAX_CLIP_SEC, out.name,
        )

        result = self._ai.generate_video_new(
            prompt=prompt,
            auto_poll=True,
            max_poll_attempts=config.META_AI_VIDEO_POLL_ATTEMPTS,
            poll_wait_seconds=config.META_AI_VIDEO_POLL_WAIT,
        )
        if result.get("error"):
            raise RuntimeError(f"Meta AI: {result['error']}")

        urls = self._urls_from_generate_video_new(result)
        if not urls:
            raise RuntimeError(
                "Meta AI returned no downloadable URLs. Refresh cookies in .env."
            )

        for url in urls:
            for attempt in range(config.DOWNLOAD_ATTEMPTS_PER_URL):
                try:
                    resp = requests.get(url, timeout=120, stream=True)
                    resp.raise_for_status()
                    data = resp.content
                    if len(data) >= config.MIN_CLIP_BYTES:
                        out.write_bytes(data)
                        self._last_source_urls = urls
                        return out
                except Exception:
                    logger.warning(
                        "Meta AI download attempt %d failed", attempt + 1, exc_info=True
                    )
                time.sleep(5)

        raise RuntimeError("Meta AI: all download URLs failed")
