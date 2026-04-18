"""Thin wrapper around `ffprobe` for measuring audio / video durations."""

from __future__ import annotations

import logging
import subprocess
from pathlib import Path

logger = logging.getLogger("cosmic_docs.ffprobe")


def probe_duration(filepath: str | Path) -> float | None:
    """Return the duration in seconds, or None if ffprobe fails."""
    import config

    path = Path(filepath)
    if not path.exists():
        return None

    try:
        result = subprocess.run(
            [
                config.FFPROBE_PATH,
                "-v", "error",
                "-show_entries", "format=duration",
                "-of", "default=noprint_wrappers=1:nokey=1",
                str(path),
            ],
            capture_output=True,
            text=True,
            timeout=30,
        )
        if result.returncode != 0:
            logger.debug("ffprobe failed for %s: %s", path, result.stderr[:200])
            return None
        duration = result.stdout.strip()
        return float(duration) if duration else None
    except (subprocess.TimeoutExpired, ValueError, FileNotFoundError):
        logger.debug("ffprobe timeout/parse error for %s", path, exc_info=True)
        return None
