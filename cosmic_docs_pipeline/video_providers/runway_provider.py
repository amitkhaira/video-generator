"""Runway Gen-4.5 video provider — 8 s clips, motion brushes."""

from __future__ import annotations

import logging
import time
from pathlib import Path

import requests

from .base import VideoProvider

logger = logging.getLogger("cosmic_docs.video.runway")


class RunwayProvider(VideoProvider):
    id = "runway"
    MAX_CLIP_SEC = 8

    def __init__(self) -> None:
        import config

        if not config.RUNWAY_API_KEY:
            raise RuntimeError("RUNWAY_API_KEY is not set")
        self._api_key = config.RUNWAY_API_KEY
        self._model = config.RUNWAY_MODEL

    def _headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self._api_key}",
            "X-Runway-Version": "2024-11-06",
            "Content-Type": "application/json",
        }

    def generate(self, prompt: str, duration: float, out_path: str | Path) -> Path:
        out = Path(out_path)
        out.parent.mkdir(parents=True, exist_ok=True)

        dur = max(5, min(int(round(duration)), self.MAX_CLIP_SEC))
        payload = {
            "model": self._model,
            "promptText": prompt,
            "duration": dur,
            "ratio": "1280:720",
        }
        logger.info("Runway submit model=%s dur=%ds → %s", self._model, dur, out.name)
        resp = requests.post(
            "https://api.dev.runwayml.com/v1/text_to_video",
            headers=self._headers(), json=payload, timeout=60,
        )
        resp.raise_for_status()
        task = resp.json()
        task_id = task.get("id")
        if not task_id:
            raise RuntimeError(f"Runway: no task id in response: {task}")

        video_url = self._poll(task_id)
        self._download(video_url, out)
        return out

    def _poll(self, task_id: str, max_attempts: int = 120, delay: int = 5) -> str:
        for attempt in range(1, max_attempts + 1):
            time.sleep(delay)
            resp = requests.get(
                f"https://api.dev.runwayml.com/v1/tasks/{task_id}",
                headers=self._headers(), timeout=30,
            )
            resp.raise_for_status()
            body = resp.json()
            status = (body.get("status") or "").upper()
            if status == "SUCCEEDED":
                outs = body.get("output") or []
                if outs:
                    return outs[0]
                raise RuntimeError(f"Runway: no output url in success response: {body}")
            if status in ("FAILED", "CANCELLED"):
                raise RuntimeError(f"Runway failed: {body}")
            logger.debug("Runway poll %d/%d status=%s", attempt, max_attempts, status)
        raise RuntimeError(f"Runway poll exhausted for task {task_id}")

    @staticmethod
    def _download(url: str, out: Path) -> None:
        resp = requests.get(url, timeout=120, stream=True)
        resp.raise_for_status()
        with open(out, "wb") as fh:
            for chunk in resp.iter_content(chunk_size=1 << 16):
                if chunk:
                    fh.write(chunk)
