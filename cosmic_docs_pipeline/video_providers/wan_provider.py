"""WAN 2.5 (Alibaba) video provider — 10 s clips, 4K, audio sync.

Accessed via third-party aggregators (Higgsfield / Pixara / ImagineArt) — all
expose roughly the same submit+poll shape. WAN_API_BASE lets you point this
at whichever aggregator you use.
"""

from __future__ import annotations

import logging
import time
from pathlib import Path

import requests

from .base import VideoProvider

logger = logging.getLogger("cosmic_docs.video.wan")


class WanProvider(VideoProvider):
    id = "wan"
    MAX_CLIP_SEC = 10

    def __init__(self) -> None:
        import config

        if not config.WAN_API_KEY:
            raise RuntimeError("WAN_API_KEY is not set")
        if not config.WAN_API_BASE:
            raise RuntimeError(
                "WAN_API_BASE is not set (e.g. https://api.higgsfield.ai). "
                "Pick an aggregator that resells WAN 2.5 and paste its base URL."
            )
        self._api_key = config.WAN_API_KEY
        self._base = config.WAN_API_BASE.rstrip("/")

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
            "model": "wan-2.5",
            "prompt": prompt,
            "duration": dur,
            "aspect_ratio": "16:9",
            "resolution": "4k",
        }
        logger.info("WAN submit dur=%ds → %s", dur, out.name)
        resp = requests.post(
            f"{self._base}/v1/videos/wan",
            headers=self._headers(), json=payload, timeout=60,
        )
        resp.raise_for_status()
        task = resp.json()
        task_id = task.get("task_id") or task.get("id")
        if not task_id:
            raise RuntimeError(f"WAN: no task id in response: {task}")

        video_url = self._poll(task_id)
        self._download(video_url, out)
        return out

    def _poll(self, task_id: str, max_attempts: int = 120, delay: int = 5) -> str:
        for attempt in range(1, max_attempts + 1):
            time.sleep(delay)
            resp = requests.get(
                f"{self._base}/v1/videos/wan/{task_id}",
                headers=self._headers(), timeout=30,
            )
            resp.raise_for_status()
            body = resp.json()
            status = (body.get("status") or "").lower()
            if status in ("completed", "succeeded", "success"):
                url = body.get("video_url") or (body.get("output") or {}).get("url")
                if url:
                    return url
                raise RuntimeError(f"WAN: no url in success response: {body}")
            if status in ("failed", "error"):
                raise RuntimeError(f"WAN failed: {body}")
            logger.debug("WAN poll %d/%d status=%s", attempt, max_attempts, status)
        raise RuntimeError(f"WAN poll exhausted for task {task_id}")

    @staticmethod
    def _download(url: str, out: Path) -> None:
        resp = requests.get(url, timeout=120, stream=True)
        resp.raise_for_status()
        with open(out, "wb") as fh:
            for chunk in resp.iter_content(chunk_size=1 << 16):
                if chunk:
                    fh.write(chunk)
