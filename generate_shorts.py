#!/usr/bin/env python3
"""
YouTube Shorts Generation Pipeline

Pipeline:
  1. Load a chunk-by-chunk Short from shorts_stories.py
  2. Generate a short video clip per chunk via MetaAI (VERTICAL orientation)
  3. Download all clips locally
  4. Generate Hindi voiceover per chunk via gTTS (with EN→HI translation)
  5. Compose each chunk: loop video to match voiceover, burn-in captions +
     on-screen text, mix audio mood track underneath
  6. Concatenate composed chunks into a single vertical Short

Usage:
  python generate_shorts.py                           # default short
  python generate_shorts.py --short sperm-whale-birth
  python generate_shorts.py --list-shorts
  python generate_shorts.py --dry-run
  python generate_shorts.py --no-audio
  python generate_shorts.py --tts-lang en
  python generate_shorts.py --no-captions
  python generate_shorts.py --no-onscreen-text
  python generate_shorts.py --cleanup
"""

from __future__ import annotations

import argparse
import json
import logging
import math
import os
import platform
import re
import shutil
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

import requests
from dotenv import load_dotenv

from shorts_stories import SHORTS, get_short, list_shorts

# ──────────────────────────────────────────────────────────────────────
# Configuration defaults
# ──────────────────────────────────────────────────────────────────────
DEFAULT_SHORT = "sperm-whale-birth"
OUTPUT_DIR = "output"
VIDEO_ORIENTATION = "VERTICAL"
RATE_LIMIT_SECONDS = 15
MAX_RETRIES = 3
RETRY_DELAY = 30
FAILED_CHUNK_EXTRA_PASSES = 3
DOWNLOAD_ATTEMPTS_PER_URL = 3
MIN_CLIP_BYTES = 1024
FFMPEG_PATH = "ffmpeg"
AUDIO_MOODS_DIR = "assets/audio_moods"
AUDIO_MOOD_VOLUME = 0.15
TTS_LANG = "hi"

CAPTION_FONT_SIZE = 52
CAPTION_WORDS_PER_GROUP = 4
CAPTION_Y_RATIO = 0.68

# ──────────────────────────────────────────────────────────────────────
# Font resolution
# ──────────────────────────────────────────────────────────────────────
_SYSTEM_FONT_CANDIDATES = [
    "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
    "/System/Library/Fonts/Supplemental/Arial.ttf",
    "/System/Library/Fonts/Helvetica.ttc",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
    "C:/Windows/Fonts/arialbd.ttf",
    "C:/Windows/Fonts/arial.ttf",
]


def _resolve_font(user_font: str | None) -> str | None:
    """Return a usable font path, or None to let FFmpeg use its default."""
    if user_font:
        if Path(user_font).exists():
            return user_font
        logger.warning("User font '%s' not found — trying system fonts.", user_font)
    for candidate in _SYSTEM_FONT_CANDIDATES:
        if Path(candidate).exists():
            return candidate
    return None


# ──────────────────────────────────────────────────────────────────────
# Logging
# ──────────────────────────────────────────────────────────────────────
logger = logging.getLogger("shorts_gen")


def setup_logging(log_dir: Path) -> None:
    logger.setLevel(logging.DEBUG)
    fmt = logging.Formatter(
        "%(asctime)s  %(levelname)-8s  %(message)s", datefmt="%Y-%m-%d %H:%M:%S"
    )
    console = logging.StreamHandler(sys.stdout)
    console.setLevel(logging.INFO)
    console.setFormatter(fmt)
    logger.addHandler(console)

    fh = logging.FileHandler(log_dir / "generation.log", encoding="utf-8")
    fh.setLevel(logging.DEBUG)
    fh.setFormatter(fmt)
    logger.addHandler(fh)


# ──────────────────────────────────────────────────────────────────────
# Validation helpers
# ──────────────────────────────────────────────────────────────────────
def load_cookies() -> dict[str, str]:
    load_dotenv()
    required = {
        "datr": os.getenv("META_AI_DATR", ""),
        "ecto_1_sess": os.getenv("META_AI_ECTO_1_SESS", ""),
    }
    missing = [k for k, v in required.items() if not v]
    if missing:
        logger.error(
            "Missing required Meta AI cookies: %s. "
            "Set them in .env (META_AI_DATR, META_AI_ECTO_1_SESS).",
            ", ".join(missing),
        )
        sys.exit(1)

    cookies = dict(required)
    for key, env_var in [
        ("abra_sess", "META_AI_ABRA_SESS"),
        ("rd_challenge", "META_AI_RD_CHALLENGE"),
        ("dpr", "META_AI_DPR"),
        ("wd", "META_AI_WD"),
    ]:
        val = os.getenv(env_var, "")
        if val:
            cookies[key] = val

    logger.debug("Loaded cookies: %s", list(cookies.keys()))
    return cookies


def check_ffmpeg(ffmpeg_path: str) -> None:
    if not shutil.which(ffmpeg_path):
        logger.error("ffmpeg not found at '%s'.", ffmpeg_path)
        sys.exit(1)
    logger.debug("ffmpeg found: %s", shutil.which(ffmpeg_path))


# ──────────────────────────────────────────────────────────────────────
# Step A — Video generation via MetaAI
# ──────────────────────────────────────────────────────────────────────
def _extract_download_urls(api_result: dict) -> list[str]:
    seen: set[str] = set()
    ordered: list[str] = []

    def _add(u: str | None) -> None:
        if u and isinstance(u, str) and u.startswith("http") and u not in seen:
            seen.add(u)
            ordered.append(u)

    for vid in api_result.get("videos", []):
        if isinstance(vid, dict):
            _add(vid.get("url"))
            _add(vid.get("fallbackUrl"))
        elif isinstance(vid, str):
            _add(vid)

    for vid in api_result.get("video_objects", []):
        if isinstance(vid, dict):
            for key in ("url", "fallbackUrl"):
                u = vid.get(key)
                if u and isinstance(u, str) and "fbcdn" in u:
                    _add(u)

    return ordered


def generate_chunk_videos(
    chunks: list[dict],
    cookies: dict[str, str],
    orientation: str,
    rate_limit: int,
    max_retries: int,
    retry_delay: int,
) -> list[dict]:
    """Call MetaAI for each chunk prompt. Returns result dicts."""
    from metaai_api import MetaAI

    ai = MetaAI(cookies=cookies)
    results: list[dict] = []

    for idx, chunk in enumerate(chunks):
        num = chunk["chunk_number"]
        prompt = chunk["video_prompt"]
        logger.info(
            "Chunk %d/%d [%s] — generating video …",
            num, len(chunks), chunk["section_type"],
        )
        logger.debug("Prompt: %s", prompt)

        url: str | None = None
        all_urls: list[str] = []
        for attempt in range(1, max_retries + 1):
            try:
                logger.info("  Attempt %d/%d …", attempt, max_retries)
                api_result = ai.generation_api.generate_video(
                    prompt=prompt, fetch_urls=True
                )
                found = _extract_download_urls(api_result)
                if found:
                    url = found[0]
                    all_urls = found
                    logger.info(
                        "  Success — %d URL(s), first: %s",
                        len(found), url[:80],
                    )
                    break
                logger.warning("  No downloadable URLs in response.")
            except Exception:
                logger.exception("  API error on attempt %d", attempt)

            if attempt < max_retries:
                wait = retry_delay * (2 ** (attempt - 1))
                logger.info("  Retrying in %ds …", wait)
                time.sleep(wait)

        if url and not all_urls:
            all_urls = [url]
        results.append({
            "chunk_number": num,
            "url": url,
            "urls": all_urls,
            "status": "success" if url else "failed",
        })

        if idx < len(chunks) - 1:
            logger.debug("Rate-limit pause: %ds", rate_limit)
            time.sleep(rate_limit)

    return results


# ──────────────────────────────────────────────────────────────────────
# Step B — Download videos
# ──────────────────────────────────────────────────────────────────────
def _chunk_video_path(chunk_number: int, output_dir: Path) -> Path:
    return output_dir / f"chunk_{chunk_number:03d}.mp4"


def clip_file_valid(path: Path) -> bool:
    try:
        return path.exists() and path.stat().st_size >= MIN_CLIP_BYTES
    except OSError:
        return False


def chunks_missing_clips(chunks: list[dict], output_dir: Path) -> list[dict]:
    return [
        c for c in chunks
        if not clip_file_valid(_chunk_video_path(c["chunk_number"], output_dir))
    ]


def download_videos(
    results: list[dict],
    output_dir: Path,
    attempts_per_url: int = DOWNLOAD_ATTEMPTS_PER_URL,
) -> list[Path]:
    downloaded: list[Path] = []

    for r in results:
        if r["status"] != "success":
            logger.warning("Skipping chunk %d (generation failed).", r["chunk_number"])
            continue

        candidate_urls: list[str] = list(r.get("urls") or [])
        if r.get("url") and r["url"] not in candidate_urls:
            candidate_urls.insert(0, r["url"])
        if not candidate_urls:
            logger.warning("Chunk %d: no URLs to download.", r["chunk_number"])
            continue

        dest = _chunk_video_path(r["chunk_number"], output_dir)
        saved = False

        for url_idx, video_url in enumerate(candidate_urls):
            for attempt in range(attempts_per_url):
                try:
                    logger.info(
                        "Downloading chunk %d (URL %d/%d, attempt %d/%d)",
                        r["chunk_number"],
                        url_idx + 1, len(candidate_urls),
                        attempt + 1, attempts_per_url,
                    )
                    resp = requests.get(video_url, stream=True, timeout=180)
                    resp.raise_for_status()
                    with open(dest, "wb") as f:
                        for data in resp.iter_content(chunk_size=1024 * 256):
                            f.write(data)

                    size = dest.stat().st_size
                    if size < MIN_CLIP_BYTES:
                        logger.warning("  File too small (%d bytes)", size)
                        dest.unlink(missing_ok=True)
                        continue

                    logger.info("  Saved %s (%.2f MB)", dest.name, size / 1024 / 1024)
                    downloaded.append(dest)
                    saved = True
                    break
                except Exception:
                    logger.exception(
                        "  Download error chunk %d (URL %d, attempt %d)",
                        r["chunk_number"], url_idx + 1, attempt + 1,
                    )
                    dest.unlink(missing_ok=True)
            if saved:
                break

        if not saved:
            logger.error("  Failed to download chunk %d.", r["chunk_number"])

    return downloaded


def merge_generation_into_results(
    results: list[dict], retry_batch: list[dict]
) -> None:
    by_num = {r["chunk_number"]: i for i, r in enumerate(results)}
    for nr in retry_batch:
        if nr["status"] != "success":
            continue
        idx = by_num.get(nr["chunk_number"])
        if idx is not None:
            results[idx] = nr


def run_failed_chunk_recovery(
    short: dict,
    results: list[dict],
    output_dir: Path,
    cookies: dict[str, str],
    orientation: str,
    rate_limit: int,
    max_retries: int,
    retry_delay: int,
    extra_passes: int,
) -> None:
    for pass_num in range(extra_passes):
        missing = chunks_missing_clips(short["chunks"], output_dir)
        if not missing:
            logger.info("All chunk clips present after recovery.")
            return

        missing_nums = {c["chunk_number"] for c in missing}

        redownload = [
            r for r in results
            if r["chunk_number"] in missing_nums
            and r["status"] == "success"
            and (r.get("urls") or r.get("url"))
        ]
        if redownload:
            logger.info(
                "Recovery pass %d/%d: re-downloading %d chunk(s) …",
                pass_num + 1, extra_passes, len(redownload),
            )
            download_videos(redownload, output_dir)
            time.sleep(min(rate_limit, 8))

        missing = chunks_missing_clips(short["chunks"], output_dir)
        if not missing:
            return

        logger.info(
            "Recovery pass %d/%d: regenerating %d chunk(s) …",
            pass_num + 1, extra_passes, len(missing),
        )
        time.sleep(rate_limit)
        retry_results = generate_chunk_videos(
            chunks=missing,
            cookies=cookies,
            orientation=orientation,
            rate_limit=rate_limit,
            max_retries=max_retries,
            retry_delay=retry_delay,
        )
        merge_generation_into_results(results, retry_results)
        download_videos(
            [r for r in retry_results if r["status"] == "success"],
            output_dir,
        )


def ordered_chunk_clip_paths(short: dict, output_dir: Path) -> list[Path]:
    clips: list[Path] = []
    for chunk in short["chunks"]:
        p = _chunk_video_path(chunk["chunk_number"], output_dir)
        if clip_file_valid(p):
            clips.append(p)
    return clips


# ──────────────────────────────────────────────────────────────────────
# Step C — Hindi voiceover via gTTS + deep_translator
# ──────────────────────────────────────────────────────────────────────
def _text_has_devanagari(text: str) -> bool:
    return any("\u0900" <= c <= "\u097f" for c in text)


def _prepare_tts_text(text: str, tts_lang: str, translate_from_en: bool) -> str:
    if not text or not text.strip():
        return text
    if tts_lang != "hi":
        return text
    if not translate_from_en or _text_has_devanagari(text):
        return text
    try:
        from deep_translator import GoogleTranslator
        return GoogleTranslator(source="en", target="hi").translate(text)
    except Exception as exc:
        logger.warning("EN→HI translation failed (%s); using original text.", exc)
        return text


def generate_voiceover_audio(
    short: dict,
    output_dir: Path,
    tts_lang: str = TTS_LANG,
    translate_to_hi: bool = True,
) -> list[Path]:
    """Generate MP3 voiceover for each chunk. Returns ordered paths."""
    from gtts import gTTS

    audio_files: list[Path] = []
    translate = translate_to_hi and tts_lang == "hi"

    for chunk in short["chunks"]:
        text = chunk.get("voiceover", "")
        if not text:
            logger.warning("  Chunk %d has no voiceover — skipping.", chunk["chunk_number"])
            continue

        audio_path = output_dir / f"voiceover_{chunk['chunk_number']:03d}.mp3"
        logger.info(
            "Generating voiceover for chunk %d [%s] (%s) …",
            chunk["chunk_number"], chunk["section_type"], tts_lang,
        )
        spoken = _prepare_tts_text(text, tts_lang, translate)
        tts = gTTS(text=spoken, lang=tts_lang, slow=False)
        tts.save(str(audio_path))
        audio_files.append(audio_path)
        logger.debug("  Saved %s", audio_path.name)

    logger.info("Generated %d voiceover files.", len(audio_files))
    return audio_files


# ──────────────────────────────────────────────────────────────────────
# Step D — Per-chunk composition helpers
# ──────────────────────────────────────────────────────────────────────
def _get_audio_duration(audio_path: Path, ffmpeg_path: str) -> float:
    ffprobe = ffmpeg_path.replace("ffmpeg", "ffprobe")
    if not shutil.which(ffprobe):
        ffprobe = "ffprobe"
    cmd = [
        ffprobe, "-v", "error",
        "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1",
        str(audio_path),
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    try:
        return float(result.stdout.strip())
    except (ValueError, AttributeError):
        logger.warning("Could not get duration for %s, defaulting to 8s", audio_path)
        return 8.0


def _escape_drawtext(text: str) -> str:
    """Escape special characters for FFmpeg drawtext filter."""
    text = text.replace("\\", "\\\\")
    text = text.replace("'", "'\\''")
    text = text.replace(":", "\\:")
    text = text.replace("%", "%%")
    return text


# ── Caption engine ────────────────────────────────────────────────────
def _build_caption_filters(
    voiceover_text: str,
    audio_duration: float,
    font_path: str | None,
    font_size: int = CAPTION_FONT_SIZE,
    words_per_group: int = CAPTION_WORDS_PER_GROUP,
    y_ratio: float = CAPTION_Y_RATIO,
) -> list[str]:
    """Build drawtext filter strings for word-group captions.

    Splits voiceover into groups of N words, each timed proportionally
    across the audio duration.
    """
    words = voiceover_text.split()
    if not words:
        return []

    groups: list[str] = []
    for i in range(0, len(words), words_per_group):
        groups.append(" ".join(words[i : i + words_per_group]))

    if not groups:
        return []

    group_duration = audio_duration / len(groups)
    filters: list[str] = []

    for idx, group_text in enumerate(groups):
        start = idx * group_duration
        end = start + group_duration
        escaped = _escape_drawtext(group_text)

        parts = [
            f"text='{escaped}'",
            f"fontsize={font_size}",
            "fontcolor=white",
            "borderw=3",
            "bordercolor=black",
            f"x=(w-text_w)/2",
            f"y=h*{y_ratio}",
            f"enable='between(t,{start:.3f},{end:.3f})'",
        ]
        if font_path:
            parts.insert(1, f"fontfile='{font_path}'")

        filters.append("drawtext=" + ":".join(parts))

    return filters


# ── On-screen text overlays ──────────────────────────────────────────
_POSITION_MAP = {
    "center":        ("(w-text_w)/2", "h*0.45"),
    "center_bottom": ("(w-text_w)/2", "h*0.82"),
    "lower_third":   ("w*0.05",       "h*0.88"),
    "top":           ("w*0.05",       "h*0.08"),
    "top_right":     ("w*0.55",       "h*0.08"),
    "label":         ("w*0.05",       "h*0.75"),
}

_STYLE_MAP = {
    "default":    {"fontsize": 36, "fontcolor": "white",  "borderw": 2, "bordercolor": "black", "box": 0},
    "bold_large": {"fontsize": 48, "fontcolor": "white",  "borderw": 3, "bordercolor": "black", "box": 0},
    "subtle":     {"fontsize": 28, "fontcolor": "white@0.8", "borderw": 1, "bordercolor": "black@0.5", "box": 0},
    "label_bg":   {"fontsize": 28, "fontcolor": "white",  "borderw": 0, "bordercolor": "black", "box": 1,
                   "boxcolor": "black@0.6", "boxborderw": 8},
}


def _build_onscreen_text_filters(
    overlays: list[dict],
    chunk_duration: float,
    font_path: str | None,
) -> list[str]:
    """Build drawtext filters for on-screen text overlays.

    Each overlay is shown for the entire chunk duration.
    """
    filters: list[str] = []

    for overlay in overlays:
        text = overlay.get("text", "")
        if not text or text == "▮":
            continue

        pos_key = overlay.get("position", "center")
        style_key = overlay.get("style", "default")

        x_expr, y_expr = _POSITION_MAP.get(pos_key, _POSITION_MAP["center"])
        style = _STYLE_MAP.get(style_key, _STYLE_MAP["default"])

        escaped = _escape_drawtext(text)

        parts = [
            f"text='{escaped}'",
            f"fontsize={style['fontsize']}",
            f"fontcolor={style['fontcolor']}",
            f"borderw={style['borderw']}",
            f"bordercolor={style['bordercolor']}",
            f"x={x_expr}",
            f"y={y_expr}",
            f"enable='between(t,0.3,{chunk_duration:.3f})'",
        ]
        if font_path:
            parts.insert(1, f"fontfile='{font_path}'")
        if style.get("box"):
            parts.append("box=1")
            parts.append(f"boxcolor={style.get('boxcolor', 'black@0.5')}")
            parts.append(f"boxborderw={style.get('boxborderw', 6)}")

        filters.append("drawtext=" + ":".join(parts))

    return filters


# ── Audio mood resolution ────────────────────────────────────────────
def _resolve_mood_audio(mood_tag: str, moods_dir: str) -> Path | None:
    """Find a mood audio file matching the tag in the moods directory."""
    mood_dir = Path(moods_dir)
    if not mood_dir.is_dir():
        return None
    for ext in (".mp3", ".wav", ".m4a", ".ogg"):
        candidate = mood_dir / f"{mood_tag}{ext}"
        if candidate.exists():
            return candidate
    return None


# ──────────────────────────────────────────────────────────────────────
# Step D — Per-chunk composition (the main composition function)
# ──────────────────────────────────────────────────────────────────────
def compose_chunks(
    short: dict,
    output_dir: Path,
    ffmpeg_path: str,
    font_path: str | None,
    moods_dir: str,
    mood_volume: float,
    enable_captions: bool,
    enable_onscreen_text: bool,
) -> list[Path]:
    """Compose each chunk: loop video + voiceover + mood audio + text overlays.

    Returns ordered list of composed clip paths.
    """
    composed: list[Path] = []

    for chunk in short["chunks"]:
        num = chunk["chunk_number"]
        video_clip = _chunk_video_path(num, output_dir)
        voiceover_path = output_dir / f"voiceover_{num:03d}.mp3"
        out_path = output_dir / f"composed_{num:03d}.mp4"

        if not video_clip.exists():
            logger.warning("No video for chunk %d — skipping.", num)
            continue

        has_voiceover = voiceover_path.exists()
        audio_duration = (
            _get_audio_duration(voiceover_path, ffmpeg_path)
            if has_voiceover else 8.0
        )

        mood_path = _resolve_mood_audio(
            chunk.get("audio_mood", ""), moods_dir
        )

        # ── Build video filter chain ──────────────────────────────
        video_filters: list[str] = []

        if enable_captions and has_voiceover:
            caption_filters = _build_caption_filters(
                chunk.get("voiceover", ""),
                audio_duration,
                font_path,
            )
            video_filters.extend(caption_filters)

        if enable_onscreen_text and chunk.get("onscreen_text"):
            onscreen_filters = _build_onscreen_text_filters(
                chunk["onscreen_text"],
                audio_duration,
                font_path,
            )
            video_filters.extend(onscreen_filters)

        # ── Build FFmpeg command ──────────────────────────────────
        inputs: list[str] = ["-stream_loop", "-1", "-i", str(video_clip)]
        if has_voiceover:
            inputs.extend(["-i", str(voiceover_path)])
        if mood_path:
            inputs.extend(["-i", str(mood_path)])

        # Determine input stream indices
        vo_idx = 1 if has_voiceover else None
        mood_idx = (2 if has_voiceover else 1) if mood_path else None

        # Audio filter graph
        audio_filter_parts: list[str] = []
        final_audio = None

        if has_voiceover and mood_path:
            audio_filter_parts.append(f"[{vo_idx}:a]volume=1.0[vo]")
            audio_filter_parts.append(
                f"[{mood_idx}:a]volume={mood_volume},"
                f"aloop=loop=-1:size=2e+09[mood]"
            )
            audio_filter_parts.append(
                "[vo][mood]amix=inputs=2:duration=first[aout]"
            )
            final_audio = "[aout]"
        elif has_voiceover:
            final_audio = f"{vo_idx}:a"
        elif mood_path:
            audio_filter_parts.append(
                f"[{mood_idx or 1}:a]volume={mood_volume},"
                f"aloop=loop=-1:size=2e+09[aout]"
            )
            final_audio = "[aout]"

        # Video filter graph
        if video_filters:
            vf_chain = ",".join(video_filters)
            video_filter_str = f"[0:v]{vf_chain}[vout]"
            final_video = "[vout]"
        else:
            video_filter_str = None
            final_video = "0:v"

        # Combine filter_complex
        all_filter_parts = list(audio_filter_parts)
        if video_filter_str:
            all_filter_parts.append(video_filter_str)

        cmd: list[str] = [ffmpeg_path, "-y"]
        cmd.extend(inputs)

        if all_filter_parts:
            cmd.extend(["-filter_complex", ";".join(all_filter_parts)])

        cmd.extend(["-map", final_video])
        if final_audio:
            if final_audio.startswith("["):
                cmd.extend(["-map", final_audio])
            else:
                cmd.extend(["-map", final_audio])

        cmd.extend([
            "-c:v", "libx264", "-preset", "medium", "-crf", "23",
        ])
        if final_audio:
            cmd.extend(["-c:a", "aac", "-b:a", "128k"])
        else:
            cmd.append("-an")

        cmd.extend(["-shortest", "-movflags", "+faststart", str(out_path)])

        logger.info(
            "Composing chunk %d [%s] (%.1fs) …",
            num, chunk["section_type"], audio_duration,
        )
        logger.debug("Command: %s", " ".join(cmd))

        proc = subprocess.run(cmd, capture_output=True, text=True)
        if proc.returncode == 0 and out_path.exists():
            composed.append(out_path)
            logger.info("  Composed → %s", out_path.name)
        else:
            logger.warning(
                "  Composition failed for chunk %d: %s",
                num, (proc.stderr or "")[-500:],
            )

    logger.info("Composed %d chunks total.", len(composed))
    return composed


# ──────────────────────────────────────────────────────────────────────
# Step E — Concatenate + finalize
# ──────────────────────────────────────────────────────────────────────
def merge_chunks(
    clips: list[Path], output_dir: Path, ffmpeg_path: str
) -> Path | None:
    if not clips:
        logger.error("No clips to merge.")
        return None

    filelist = output_dir / "filelist.txt"
    with open(filelist, "w") as f:
        for clip in clips:
            f.write(f"file '{clip.resolve()}'\n")

    final = output_dir / "final_short.mp4"

    cmd_copy = [
        ffmpeg_path, "-y",
        "-f", "concat", "-safe", "0",
        "-i", str(filelist),
        "-c", "copy", "-movflags", "+faststart",
        str(final),
    ]
    logger.info("Merging %d chunks (stream-copy) …", len(clips))
    proc = subprocess.run(cmd_copy, capture_output=True, text=True)

    if proc.returncode == 0 and final.exists() and final.stat().st_size > 0:
        logger.info("Merge complete (stream-copy): %s", final)
        return final

    logger.warning("Stream-copy merge failed — re-encoding.")
    cmd_reencode = [
        ffmpeg_path, "-y",
        "-f", "concat", "-safe", "0",
        "-i", str(filelist),
        "-c:v", "libx264", "-preset", "medium", "-crf", "23",
        "-c:a", "aac", "-b:a", "128k",
        "-movflags", "+faststart",
        str(final),
    ]
    proc2 = subprocess.run(cmd_reencode, capture_output=True, text=True)

    if proc2.returncode == 0 and final.exists() and final.stat().st_size > 0:
        logger.info("Merge complete (re-encoded): %s", final)
        return final

    logger.error("All merge strategies failed: %s", (proc2.stderr or "")[-2000:])
    return None


# ──────────────────────────────────────────────────────────────────────
# CLI & main
# ──────────────────────────────────────────────────────────────────────
def parse_args() -> argparse.Namespace:
    load_dotenv()
    parser = argparse.ArgumentParser(
        description="Generate a YouTube Short from chunk-by-chunk story prompts."
    )
    parser.add_argument(
        "--short", default=DEFAULT_SHORT,
        help=f"Short slug to generate (default: {DEFAULT_SHORT})",
    )
    parser.add_argument(
        "--list-shorts", action="store_true",
        help="List available shorts and exit.",
    )
    parser.add_argument(
        "--output-dir", default=OUTPUT_DIR,
        help=f"Base output directory (default: {OUTPUT_DIR})",
    )
    parser.add_argument(
        "--orientation", default=VIDEO_ORIENTATION,
        choices=["LANDSCAPE", "VERTICAL", "SQUARE"],
        help=f"Video orientation (default: {VIDEO_ORIENTATION})",
    )
    parser.add_argument(
        "--rate-limit", type=int, default=RATE_LIMIT_SECONDS,
        help=f"Seconds between API calls (default: {RATE_LIMIT_SECONDS})",
    )
    parser.add_argument(
        "--max-retries", type=int, default=MAX_RETRIES,
        help=f"Max retries per failed chunk (default: {MAX_RETRIES})",
    )
    parser.add_argument(
        "--retry-delay", type=int, default=RETRY_DELAY,
        help=f"Base retry delay in seconds (default: {RETRY_DELAY})",
    )
    parser.add_argument(
        "--ffmpeg", default=FFMPEG_PATH,
        help=f"Path to ffmpeg binary (default: {FFMPEG_PATH})",
    )
    parser.add_argument(
        "--font", default=None,
        help="Path to a .ttf font file for text overlays.",
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Validate config and print chunk prompts without calling APIs.",
    )
    parser.add_argument(
        "--cleanup", action="store_true",
        help="Delete individual chunk clips after successful merge.",
    )
    parser.add_argument(
        "--no-audio", action="store_true",
        help="Skip voiceover generation (video-only output).",
    )
    parser.add_argument(
        "--no-captions", action="store_true",
        help="Skip burned-in voiceover captions.",
    )
    parser.add_argument(
        "--no-onscreen-text", action="store_true",
        help="Skip on-screen text overlays.",
    )
    parser.add_argument(
        "--tts-lang",
        default=os.getenv("VIDEO_TTS_LANG", TTS_LANG),
        help="gTTS language code: hi (Hindi, default), en, etc.",
    )
    parser.add_argument(
        "--no-translate-narration", action="store_true",
        help="Skip EN→HI translation (use when voiceover is already in Hindi).",
    )
    parser.add_argument(
        "--audio-moods-dir", default=AUDIO_MOODS_DIR,
        help=f"Directory containing mood audio files (default: {AUDIO_MOODS_DIR})",
    )
    parser.add_argument(
        "--mood-volume", type=float, default=AUDIO_MOOD_VOLUME,
        help=f"Audio mood track volume (default: {AUDIO_MOOD_VOLUME})",
    )
    parser.add_argument(
        "--failed-chunk-passes", type=int, default=FAILED_CHUNK_EXTRA_PASSES,
        help="Recovery passes for failed/missing chunks (default: %(default)s)",
    )
    return parser.parse_args()


def print_summary(
    title: str,
    results: list[dict],
    final_path: Path | None,
    run_dir: Path,
    elapsed: float,
    audio_enabled: bool,
    tts_lang: str | None = None,
) -> None:
    success = sum(1 for r in results if r["status"] == "success")
    failed = sum(1 for r in results if r["status"] == "failed")
    logger.info("=" * 60)
    logger.info("GENERATION SUMMARY")
    logger.info("  Short:     %s", title)
    logger.info("  Chunks:    %d total, %d succeeded, %d failed", len(results), success, failed)
    if audio_enabled and tts_lang:
        logger.info("  Audio:     enabled (TTS lang=%s)", tts_lang)
    else:
        logger.info("  Audio:     disabled")
    logger.info("  Output:    %s", run_dir)
    if final_path:
        size_mb = final_path.stat().st_size / 1024 / 1024
        logger.info("  Final:     %s (%.2f MB)", final_path.name, size_mb)
    else:
        logger.info("  Final:     NONE (merge failed or no clips)")
    logger.info("  Elapsed:   %.1f seconds", elapsed)
    logger.info("=" * 60)


def main() -> None:
    args = parse_args()

    # --list-shorts
    if args.list_shorts:
        print("\nAvailable shorts:\n")
        for slug, title in list_shorts():
            print(f"  {slug:30s}  {title}")
        print()
        return

    # Load short
    short = get_short(args.short)
    if short is None:
        available = ", ".join(s for s, _ in list_shorts())
        print(f"Error: unknown short '{args.short}'. Available: {available}")
        sys.exit(1)

    # Create output directory
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    run_dir = Path(args.output_dir) / f"short-{args.short}_{timestamp}"
    run_dir.mkdir(parents=True, exist_ok=True)

    setup_logging(run_dir)
    font_path = _resolve_font(args.font)

    logger.info("Short: %s — \"%s\"", args.short, short["title"])
    logger.info("Chunks: %d  (~%ds total)", len(short["chunks"]), short.get("total_duration", 0))
    logger.info("Orientation: %s", args.orientation)
    logger.info("Audio: %s", "disabled (--no-audio)" if args.no_audio else "enabled")
    if not args.no_audio:
        logger.info("TTS language: %s", args.tts_lang)
    logger.info("Captions: %s", "disabled" if args.no_captions else "enabled")
    logger.info("On-screen text: %s", "disabled" if args.no_onscreen_text else "enabled")
    logger.info("Font: %s", font_path or "(ffmpeg default)")
    logger.info("Audio moods dir: %s", args.audio_moods_dir)
    logger.info("Output: %s", run_dir)

    # --dry-run
    if args.dry_run:
        logger.info("\nDRY RUN — validating configuration.\n")

        if shutil.which(args.ffmpeg):
            logger.info("ffmpeg: OK (%s)", shutil.which(args.ffmpeg))
        else:
            logger.warning("ffmpeg: NOT FOUND at '%s'", args.ffmpeg)

        load_dotenv()
        for var, req in [("META_AI_DATR", True), ("META_AI_ECTO_1_SESS", True)]:
            val = os.getenv(var, "")
            if val:
                logger.info("Cookie %s: OK", var)
            elif req:
                logger.warning("Cookie %s: MISSING (required)", var)

        moods_dir = Path(args.audio_moods_dir)
        logger.info("\n--- Chunk Prompts ---\n")
        for chunk in short["chunks"]:
            mood_file = _resolve_mood_audio(chunk.get("audio_mood", ""), args.audio_moods_dir)
            logger.info(
                "Chunk %d [%s] %s",
                chunk["chunk_number"],
                chunk["section_type"],
                chunk["time_range"],
            )
            logger.info("  Video:     %s", chunk["video_prompt"][:120] + "…")
            if chunk.get("voiceover"):
                logger.info("  Voiceover: %s", chunk["voiceover"][:120])
            if chunk.get("onscreen_text"):
                texts = [o["text"] for o in chunk["onscreen_text"] if o.get("text")]
                logger.info("  On-screen: %s", " | ".join(texts))
            logger.info("  Mood:      %s → %s",
                         chunk.get("audio_mood", "none"),
                         mood_file or "(not found)")
            logger.info("")

        logger.info("Estimated total: ~%ds", short.get("total_duration", 0))
        logger.info("Dry run complete.")
        return

    # ── Full run ──────────────────────────────────────────────────
    check_ffmpeg(args.ffmpeg)
    cookies = load_cookies()

    t_start = time.time()
    results: list[dict] = []

    try:
        # Step A — generate chunk videos
        results = generate_chunk_videos(
            chunks=short["chunks"],
            cookies=cookies,
            orientation=args.orientation,
            rate_limit=args.rate_limit,
            max_retries=args.max_retries,
            retry_delay=args.retry_delay,
        )

        # Step B — download + recovery
        download_videos(results, run_dir)
        run_failed_chunk_recovery(
            short=short,
            results=results,
            output_dir=run_dir,
            cookies=cookies,
            orientation=args.orientation,
            rate_limit=args.rate_limit,
            max_retries=args.max_retries,
            retry_delay=args.retry_delay,
            extra_passes=args.failed_chunk_passes,
        )

        # Step C — voiceover
        if not args.no_audio:
            generate_voiceover_audio(
                short,
                run_dir,
                tts_lang=args.tts_lang,
                translate_to_hi=not args.no_translate_narration,
            )

        # Step D — compose each chunk (video + voiceover + captions + text + mood)
        composed = compose_chunks(
            short=short,
            output_dir=run_dir,
            ffmpeg_path=args.ffmpeg,
            font_path=font_path,
            moods_dir=args.audio_moods_dir,
            mood_volume=args.mood_volume,
            enable_captions=not args.no_captions and not args.no_audio,
            enable_onscreen_text=not args.no_onscreen_text,
        )

        # Fall back to raw clips if composition produced nothing
        clips = ordered_chunk_clip_paths(short, run_dir)
        merge_input = composed if composed else clips

        # Step E — merge
        final_path = merge_chunks(merge_input, run_dir, args.ffmpeg)

        # Cleanup
        if args.cleanup and final_path:
            logger.info("Cleaning up intermediate files …")
            for clip in clips:
                clip.unlink(missing_ok=True)
            for p in run_dir.glob("composed_*.mp4"):
                p.unlink(missing_ok=True)
            for p in run_dir.glob("voiceover_*.mp3"):
                p.unlink(missing_ok=True)
            filelist = run_dir / "filelist.txt"
            filelist.unlink(missing_ok=True)

    except KeyboardInterrupt:
        logger.warning("Interrupted! Merging available clips …")
        existing = sorted(run_dir.glob("chunk_*.mp4"))
        if existing:
            final_path = merge_chunks(existing, run_dir, args.ffmpeg)
        else:
            final_path = None

    elapsed = time.time() - t_start
    print_summary(
        short["title"],
        results,
        final_path,
        run_dir,
        elapsed,
        not args.no_audio,
        tts_lang=args.tts_lang if not args.no_audio else None,
    )


if __name__ == "__main__":
    main()
