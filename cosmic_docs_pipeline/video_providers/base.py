"""Abstract video provider contract.

Each provider must expose `MAX_CLIP_SEC` so the timeline planner can decide
whether script beats need to be split into scene-continuation chains, and
a `generate(prompt, duration, out_path) -> Path` method.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path


class VideoProvider(ABC):
    """Base class for every AI video generation backend."""

    id: str = "base"
    # Maximum clip length (seconds) the backend can produce in a single call.
    # Used by 03_audio_timeline.py to decide beat splitting.
    MAX_CLIP_SEC: int = 5

    @abstractmethod
    def generate(self, prompt: str, duration: float, out_path: str | Path) -> Path:
        """Generate a clip of approximately `duration` seconds and save to `out_path`.

        Returns the Path to the saved MP4.
        Raises RuntimeError if generation fails after all retries.
        """
        ...
