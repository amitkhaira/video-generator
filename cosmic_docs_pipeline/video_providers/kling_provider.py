"""Kling 2.6 / 3.0 video provider — up to 60-120 s single clip.

Kills scene-continuation complexity for most beats. Requires KLING_API_KEY.

Note: the exact Kling REST surface has shifted between Kling Cloud, KreaSys,
and several aggregators during 2025-2026. This implementation targets the
standard task-based flow (submit → poll → fetch video URL). Adjust the
`_ENDPOINTS` block if your provider uses a slightly different path layout.
"""

from __future__ import annotations

import logging
import time
from pathlib import Path

import requests

from .base import VideoProvider

logger = logging.getLogger("cosmic_docs.video.kling")

_ENDPOINTS = {
    "submit": "https://api.klingai.com/v1/videos/text2video",
    "poll":   "https://api.klingai.com/v1/videos/text2video/{task_id}",
}


class KlingProvider(VideoProvider):
    id = "kling"
    MAX_CLIP_SEC = 60  # conservative; Pro tier goes to 120 s

    def __init__(self) -> None:
        import config

        if not config.KLING_API_KEY:
            raise RuntimeError("KLING_API_KEY is not set")
        self._api_key = config.KLING_API_KEY
        self._model = config.KLING_MODEL

    def _headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
        }

    def generate(self, prompt: str, duration: float, out_path: str | Path) -> Path:
        out = Path(out_path)
        out.parent.mkdir(parents=True, exist_ok=True)

        dur = max(5, min(int(round(duration)), self.MAX_CLIP_SEC))
        payload = {
            "model_name": self._model,
            "prompt": prompt,
            "duration": str(dur),
            "aspect_ratio": "16:9",
            "cfg_scale": 0.5,
        }

        logger.info(
            "Kling submit model=%s duration=%ds → %s",
            self._model, dur, out.name,
        )
        resp = requests.post(
            _ENDPOINTS["submit"], headers=self._headers(), json=payload, timeout=60
        )
        resp.raise_for_status()
        data = resp.json()
        task_id = (data.get("data") or {}).get("task_id") or data.get("task_id")
        if not task_id:
            raise RuntimeError(f"Kling submit: no task_id in response: {data}")

        video_url = self._poll(task_id)
        self._download(video_url, out)
        return out

    def _poll(self, task_id: str, max_attempts: int = 60, delay: int = 5) -> str:
        url = _ENDPOINTS["poll"].format(task_id=task_id)
        for attempt in range(1, max_attempts + 1):
            time.sleep(delay)
            resp = requests.get(url, headers=self._headers(), timeout=30)
            resp.raise_for_status()
            body = resp.json()
            data = body.get("data") or {}
            status = (data.get("task_status") or "").lower()
            if status in ("succeed", "success", "completed"):
                videos = (data.get("task_result") or {}).get("videos") or []
                if videos and videos[0].get("url"):
                    return videos[0]["url"]
                raise RuntimeError(f"Kling succeed but no video url: {body}")
            if status in ("failed", "error"):
                raise RuntimeError(f"Kling task failed: {body}")
            logger.debug(
                "Kling poll %d/%d status=%s", attempt, max_attempts, status or "pending"
            )
        raise RuntimeError(f"Kling poll exhausted for task {task_id}")

    @staticmethod
    def _download(url: str, out: Path) -> None:
        resp = requests.get(url, timeout=120, stream=True)
        resp.raise_for_status()
        with open(out, "wb") as fh:
            for chunk in resp.iter_content(chunk_size=1 << 16):
                if chunk:
                    fh.write(chunk)
