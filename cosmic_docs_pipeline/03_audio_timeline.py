#!/usr/bin/env python3
"""Stage 03 — Audio Timeline Builder.

Walks output/<topic>/beats/*.wav, probes each duration with ffprobe, and
emits timeline.json. Uses the selected video provider's MAX_CLIP_SEC to
decide which beats need scene-continuation splits.

INPUT:
    output/<topic>/script.json        — from stage 01
    output/<topic>/beats/NNN.wav      — from stage 02

OUTPUT:
    output/<topic>/timeline.json
"""

from __future__ import annotations

import argparse
import json
import logging
import math
import sys
from pathlib import Path

import config
from utils.ffprobe import probe_duration

logger = logging.getLogger("cosmic_docs.stage03")


def _setup_logging() -> None:
    logger.setLevel(logging.DEBUG)
    fmt = logging.Formatter("%(asctime)s  %(levelname)-7s  %(message)s", "%H:%M:%S")
    console = logging.StreamHandler(sys.stdout)
    console.setLevel(logging.INFO)
    console.setFormatter(fmt)
    logger.addHandler(console)


def _split_durations(total: float, max_clip: int) -> list[float]:
    """Evenly distribute `total` across clips of at most `max_clip` seconds each.

    Ensures every slice is at least 2 s to avoid unusable micro-clips.
    """
    n = max(1, math.ceil(total / max_clip))
    base = total / n
    if base < 2.0 and total > 2.0:
        # Reduce n so each slice stays ≥ 2 s
        n = max(1, math.floor(total / 2.0))
        n = max(1, min(n, math.ceil(total / max_clip)))
        base = total / n
    return [round(base, 2)] * n


def _parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Stage 03 — Audio Timeline Builder")
    parser.add_argument(
        "--max-clip-sec", type=int, default=None,
        help="override VIDEO_MAX_CLIP_SEC from config",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    _setup_logging()
    args = _parse_args(argv if argv is not None else sys.argv[1:])

    output_dir = Path(config.output_dir_path())
    beats_dir = Path(config.beats_dir_path())
    script_path = output_dir / "script.json"

    if not script_path.exists():
        logger.error("script.json missing (%s) — run 01 first", script_path)
        return 2

    script = json.loads(script_path.read_text(encoding="utf-8"))

    max_clip = args.max_clip_sec or config.resolve_video_max_clip_sec()
    logger.info(
        "Provider=%s  MAX_CLIP_SEC=%d  beats=%d",
        config.VIDEO_PROVIDER, max_clip, len(script["beats"]),
    )

    timeline_beats = []
    total_audio = 0.0
    total_clips = 0

    for beat in script["beats"]:
        beat_id = beat["id"]
        wav = beats_dir / f"{beat_id:03d}.wav"
        if not wav.exists():
            logger.warning("Missing %s — falling back to est_sec=%s", wav.name, beat.get("est_sec"))
            audio_sec = float(beat.get("est_sec", 4.0))
        else:
            measured = probe_duration(wav)
            audio_sec = measured if measured is not None else float(beat.get("est_sec", 4.0))

        needs_split = audio_sec > max_clip + 0.15  # 150 ms tolerance
        if needs_split:
            clip_durations = _split_durations(audio_sec, max_clip)
        else:
            clip_durations = [round(audio_sec, 2)]

        timeline_beats.append({
            "id": beat_id,
            "section_id": beat.get("section_id"),
            "text": beat["text"],
            "audio_sec": round(audio_sec, 3),
            "needs_split": needs_split,
            "clip_count": len(clip_durations),
            "clip_durations": clip_durations,
        })
        total_audio += audio_sec
        total_clips += len(clip_durations)

    timeline = {
        "video_provider": config.VIDEO_PROVIDER,
        "video_max_clip_sec": max_clip,
        "total_audio_sec": round(total_audio, 2),
        "total_clips": total_clips,
        "beats": timeline_beats,
    }
    out_path = output_dir / "timeline.json"
    out_path.write_text(json.dumps(timeline, ensure_ascii=False, indent=2), encoding="utf-8")

    mins = total_audio / 60.0
    logger.info(
        "Wrote %s  total_audio=%.1fs (%.1f min)  total_clips=%d",
        out_path.name, total_audio, mins, total_clips,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
