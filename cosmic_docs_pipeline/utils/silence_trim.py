"""Aggressive silence trimming via ffmpeg's `silenceremove` filter.

Removes any silent gap longer than `stop_duration` seconds whose level is
below `stop_threshold_db`. Default tuning (0.35 s / -38 dB) matches the
Quera Official "flow" feel while keeping natural phrasing pauses (~200 ms).
"""

from __future__ import annotations

import logging
import shutil
import subprocess
from pathlib import Path

logger = logging.getLogger("cosmic_docs.silence_trim")


def trim_silence(
    src: str | Path,
    dst: str | Path,
    *,
    stop_duration: float | None = None,
    stop_threshold_db: int | None = None,
) -> Path:
    """Trim silence from `src` and write to `dst`. Returns Path(dst).

    Args:
        src: input audio file (wav recommended).
        dst: output file path (wav). Created/overwritten.
        stop_duration: seconds of silence above which to trim. Defaults to
            `config.SILENCE_TRIM_DURATION`.
        stop_threshold_db: dB below which audio is considered silence. Defaults
            to `config.SILENCE_TRIM_THRESHOLD_DB`.
    """
    import config

    stop_duration = (
        config.SILENCE_TRIM_DURATION if stop_duration is None else stop_duration
    )
    stop_threshold_db = (
        config.SILENCE_TRIM_THRESHOLD_DB
        if stop_threshold_db is None
        else stop_threshold_db
    )

    src_path = Path(src)
    dst_path = Path(dst)
    dst_path.parent.mkdir(parents=True, exist_ok=True)

    if not src_path.exists():
        raise FileNotFoundError(f"silence_trim: input missing: {src_path}")

    # stop_periods=-1 means "remove ALL silent regions" (start, middle, end).
    silence_filter = (
        f"silenceremove="
        f"stop_periods=-1:"
        f"stop_duration={stop_duration}:"
        f"stop_threshold={stop_threshold_db}dB"
    )

    cmd = [
        config.FFMPEG_PATH,
        "-y",
        "-i", str(src_path),
        "-af", silence_filter,
        "-ar", "24000",
        "-ac", "1",
        str(dst_path),
    ]

    logger.debug(
        "silenceremove dur=%ss thresh=%sdB  %s → %s",
        stop_duration, stop_threshold_db, src_path.name, dst_path.name,
    )
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode != 0:
        # If ffmpeg failed (unexpected codec, etc.), fall back to copying the
        # source file so the pipeline can still progress.
        logger.warning(
            "ffmpeg silenceremove failed (exit %d), copying src unchanged:\n%s",
            proc.returncode, proc.stderr[:500],
        )
        shutil.copyfile(src_path, dst_path)

    return dst_path
