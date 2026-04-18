"""Sora 2 video provider (OpenAI) — cinematic premium, 10 s clips."""

from __future__ import annotations

import logging
import time
from pathlib import Path

import requests

from .base import VideoProvider

logger = logging.getLogger("cosmic_docs.video.sora")


class SoraProvider(VideoProvider):
    id = "sora"
    MAX_CLIP_SEC = 10

    def __init__(self) -> None:
        import config

        # Sora access in 2026 ships through the OpenAI API once you're on a
        # paid tier; we read SORA_API_KEY (falls back to OPENAI_API_KEY).
        self._api_key = config.SORA_API_KEY or config.OPENAI_API_KEY
        if not self._api_key:
            raise RuntimeError("SORA_API_KEY (or OPENAI_API_KEY) is not set")

    def generate(self, prompt: str, duration: float, out_path: str | Path) -> Path:
        out = Path(out_path)
        out.parent.mkdir(parents=True, exist_ok=True)

        dur = max(4, min(int(round(duration)), self.MAX_CLIP_SEC))
        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": "sora-2",
            "prompt": prompt,
            "duration_seconds": dur,
            "aspect_ratio": "16:9",
            "resolution": "1080p",
        }

        logger.info("Sora submit duration=%ds → %s", dur, out.name)
        try:
            submit = requests.post(
                "https://api.openai.com/v1/videos",
                headers=headers, json=payload, timeout=60,
            )
            submit.raise_for_status()
        except requests.HTTPError as exc:
            raise RuntimeError(
                f"Sora submit failed ({submit.status_code}): {submit.text[:500]}"
            ) from exc

        job = submit.json()
        job_id = job.get("id") or job.get("video", {}).get("id")
        if not job_id:
            raise RuntimeError(f"Sora: no job id in response: {job}")

        video_url = self._poll(job_id, headers)
        self._download(video_url, out)
        return out

    def _poll(self, job_id: str, headers: dict, max_attempts: int = 60, delay: int = 5) -> str:
        for attempt in range(1, max_attempts + 1):
            time.sleep(delay)
            resp = requests.get(
                f"https://api.openai.com/v1/videos/{job_id}",
                headers=headers, timeout=30,
            )
            resp.raise_for_status()
            body = resp.json()
            status = (body.get("status") or "").lower()
            if status in ("completed", "succeeded", "success"):
                url = body.get("video_url") or (body.get("output") or {}).get("url")
                if url:
                    return url
                raise RuntimeError(f"Sora completed but no url: {body}")
            if status in ("failed", "error"):
                raise RuntimeError(f"Sora failed: {body}")
            logger.debug("Sora poll %d/%d status=%s", attempt, max_attempts, status)
        raise RuntimeError(f"Sora poll exhausted for job {job_id}")

    @staticmethod
    def _download(url: str, out: Path) -> None:
        resp = requests.get(url, timeout=120, stream=True)
        resp.raise_for_status()
        with open(out, "wb") as fh:
            for chunk in resp.iter_content(chunk_size=1 << 16):
                if chunk:
                    fh.write(chunk)
