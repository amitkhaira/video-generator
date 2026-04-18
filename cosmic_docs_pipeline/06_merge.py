#!/usr/bin/env python3
"""Stage 06 — Merge clips + voiceover into final_video.mp4.

Steps:
  1. Order clips by timeline beat/clip_index.
  2. Scale/pad each clip to a uniform 1920×1080 (or configurable).
  3. Re-time each clip to exactly match its target `duration_sec` from timeline.
  4. Concat all clips into video_track.mp4.
  5. Overlay voiceover.wav as the master audio; pad/crop video to match.
  6. Produce YouTube chapter markers from script.json sections.
  7. Write final_video.mp4 and chapters.txt.
"""

from __future__ import annotations

import argparse
import json
import logging
import subprocess
import sys
import tempfile
from pathlib import Path

import config
from utils.ffprobe import probe_duration

logger = logging.getLogger("cosmic_docs.stage06")


def _setup_logging() -> None:
    logger.setLevel(logging.DEBUG)
    fmt = logging.Formatter("%(asctime)s  %(levelname)-7s  %(message)s", "%H:%M:%S")
    console = logging.StreamHandler(sys.stdout)
    console.setLevel(logging.INFO)
    console.setFormatter(fmt)
    logger.addHandler(console)


def _retime_clip(src: Path, target_sec: float, dst: Path) -> None:
    """Re-time a clip so its output duration == target_sec.

    Uses atempo via setpts ratio to stretch or shrink uniformly.
    Also normalizes to 1920×1080 and strips the source audio (voiceover is master).
    """
    src_dur = probe_duration(src) or target_sec
    if src_dur <= 0.1:
        src_dur = target_sec

    # setpts = PTS * (target / source); if source is shorter than target we slow, longer we speed up
    ratio = target_sec / src_dur
    vf = (
        "scale=1920:1080:force_original_aspect_ratio=decrease,"
        "pad=1920:1080:(ow-iw)/2:(oh-ih)/2:color=black,"
        f"setpts={ratio:.6f}*PTS"
    )

    cmd = [
        config.FFMPEG_PATH, "-y",
        "-i", str(src),
        "-an",
        "-vf", vf,
        "-t", f"{target_sec:.3f}",
        "-r", "30",
        "-c:v", "libx264", "-preset", "medium", "-crf", "20",
        "-pix_fmt", "yuv420p",
        str(dst),
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode != 0:
        raise RuntimeError(f"ffmpeg retime failed: {proc.stderr[:500]}")


def _concat(segments: list[Path], out_path: Path) -> None:
    with tempfile.NamedTemporaryFile("w", suffix=".txt", delete=False, encoding="utf-8") as fh:
        list_file = Path(fh.name)
        for s in segments:
            fh.write(f"file '{s.resolve()}'\n")
    try:
        cmd = [
            config.FFMPEG_PATH, "-y",
            "-f", "concat",
            "-safe", "0",
            "-i", str(list_file),
            "-c", "copy",
            str(out_path),
        ]
        proc = subprocess.run(cmd, capture_output=True, text=True)
        if proc.returncode != 0:
            # Reencode concat fallback
            cmd = [
                config.FFMPEG_PATH, "-y",
                "-f", "concat",
                "-safe", "0",
                "-i", str(list_file),
                "-c:v", "libx264", "-preset", "medium", "-crf", "20",
                "-pix_fmt", "yuv420p",
                "-r", "30",
                str(out_path),
            ]
            proc = subprocess.run(cmd, capture_output=True, text=True)
            if proc.returncode != 0:
                raise RuntimeError(f"ffmpeg concat failed: {proc.stderr[:500]}")
    finally:
        list_file.unlink(missing_ok=True)


def _mux_audio(video: Path, audio: Path, out: Path) -> None:
    """Overlay voiceover as master audio; shortest of the two wins."""
    cmd = [
        config.FFMPEG_PATH, "-y",
        "-i", str(video),
        "-i", str(audio),
        "-map", "0:v:0",
        "-map", "1:a:0",
        "-c:v", "copy",
        "-c:a", "aac", "-b:a", "192k",
        "-shortest",
        "-movflags", "+faststart",
        str(out),
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode != 0:
        raise RuntimeError(f"ffmpeg mux failed: {proc.stderr[:500]}")


def _fmt_chapter_time(sec: float) -> str:
    sec = max(0, int(sec))
    h = sec // 3600
    m = (sec % 3600) // 60
    s = sec % 60
    if h:
        return f"{h:d}:{m:02d}:{s:02d}"
    return f"{m:d}:{s:02d}"


def _write_chapters(script: dict, timeline: dict, out_path: Path) -> None:
    """Build YouTube chapter markers from the timeline beats mapped to sections.

    Must start at 0:00 per YouTube's chapter rules.
    """
    # Map beat_id → start_sec based on accumulated audio durations from timeline.
    accum = 0.0
    beat_start: dict[int, float] = {}
    for beat in timeline["beats"]:
        beat_start[beat["id"]] = accum
        accum += beat["audio_sec"]

    section_map = {s["id"]: s.get("title", s["id"]) for s in script.get("sections", [])}

    # Walk beats in order, record start time of each new section_id.
    chapters: list[tuple[float, str]] = []
    seen: set[str] = set()
    for beat in timeline["beats"]:
        sec_id = beat.get("section_id")
        if sec_id and sec_id not in seen:
            title = section_map.get(sec_id, sec_id).title()
            chapters.append((beat_start[beat["id"]], title))
            seen.add(sec_id)

    if not chapters:
        chapters = [(0.0, "Start")]
    # YouTube requires first chapter at 0:00.
    chapters[0] = (0.0, chapters[0][1])

    lines = [f"{_fmt_chapter_time(t)} {title}" for t, title in chapters]
    out_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Stage 06 — Merge")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    _setup_logging()
    _parse_args(argv if argv is not None else sys.argv[1:])

    output_dir = Path(config.output_dir_path())
    clips_dir = Path(config.clips_dir_path())

    timeline_path = output_dir / "timeline.json"
    script_path = output_dir / "script.json"
    voiceover_path = output_dir / "voiceover.wav"

    for p in (timeline_path, script_path, voiceover_path):
        if not p.exists():
            logger.error("missing %s", p)
            return 2

    timeline = json.loads(timeline_path.read_text(encoding="utf-8"))
    script = json.loads(script_path.read_text(encoding="utf-8"))

    retimed_dir = output_dir / "_retimed"
    retimed_dir.mkdir(parents=True, exist_ok=True)

    ordered_segments: list[Path] = []
    missing = 0
    for beat in timeline["beats"]:
        for clip_idx, dur in enumerate(beat["clip_durations"]):
            src = clips_dir / f"{beat['id']:03d}_{clip_idx:02d}.mp4"
            if not src.exists():
                logger.warning("missing clip %s — inserting black fallback (%.2fs)", src.name, dur)
                missing += 1
                src = _make_black(src, dur, retimed_dir)
            retimed = retimed_dir / f"{beat['id']:03d}_{clip_idx:02d}.mp4"
            _retime_clip(src, dur, retimed)
            ordered_segments.append(retimed)

    if missing:
        logger.warning("Replaced %d missing clips with black fallback", missing)

    video_track = output_dir / "video_track.mp4"
    _concat(ordered_segments, video_track)
    logger.info("Concatenated video track → %s", video_track.name)

    final_path = output_dir / "final_video.mp4"
    _mux_audio(video_track, voiceover_path, final_path)

    chapters_path = output_dir / "chapters.txt"
    _write_chapters(script, timeline, chapters_path)

    actual = probe_duration(final_path)
    logger.info(
        "✔ final_video.mp4 ready (duration=%.2fs)  chapters=%s",
        actual or -1, chapters_path.name,
    )
    return 0


def _make_black(orig_src: Path, duration: float, dest_dir: Path) -> Path:
    """Create a black placeholder clip for a missing upstream source."""
    dest = dest_dir / f"missing_{orig_src.stem}.mp4"
    cmd = [
        config.FFMPEG_PATH, "-y",
        "-f", "lavfi", "-i", f"color=c=black:s=1920x1080:d={duration}:r=30",
        "-c:v", "libx264", "-preset", "ultrafast", "-crf", "28",
        "-pix_fmt", "yuv420p",
        str(dest),
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode != 0:
        raise RuntimeError(f"ffmpeg black fallback failed: {proc.stderr[:500]}")
    return dest


if __name__ == "__main__":
    raise SystemExit(main())
