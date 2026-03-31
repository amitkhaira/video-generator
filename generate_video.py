#!/usr/bin/env python3
"""
Daily Video Generation from Classic Stories (Panchatantra)

Pipeline:
  1. Load a pre-written story from stories.py
  2. Generate a character reference image and upload it to MetaAI
  3. Generate a short video clip for each scene via MetaAI (image-to-video)
  4. Download all clips locally
  5. Generate narration audio per scene via gTTS
  6. Compose each scene: loop video to match narration, overlay audio
  7. Merge narrated scenes into a single MP4 with background music

Usage:
  python generate_video.py                        # normal run
  python generate_video.py --dry-run              # validate config, print prompts, skip API
  python generate_video.py --story blue-jackal    # pick a different story
  python generate_video.py --list-stories         # show available story slugs
  python generate_video.py --cleanup              # delete individual clips after merge
  python generate_video.py --no-audio             # skip narration + music (video only)
  python generate_video.py --tts-lang hi          # Hindi narration (default)
  python generate_video.py --tts-lang en          # English narration
  python generate_video.py --no-translate-narration  # Hindi TTS; text already in Devanagari
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import shutil
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

import requests
from dotenv import load_dotenv

from stories import STORIES, get_story, list_stories

# ──────────────────────────────────────────────────────────────────────
# Configuration defaults (override via CLI flags or env vars)
# ──────────────────────────────────────────────────────────────────────
STORY_SLUG = "monkey-and-crocodile"
OUTPUT_DIR = "output"
VIDEO_ORIENTATION = "LANDSCAPE"  # LANDSCAPE | VERTICAL | SQUARE
RATE_LIMIT_SECONDS = 15
MAX_RETRIES = 3
RETRY_DELAY = 30
FAILED_SCENE_EXTRA_PASSES = 3  # After main run, retry gen+download for missing clips
DOWNLOAD_ATTEMPTS_PER_URL = 3
MIN_CLIP_BYTES = 1024  # Treat smaller files as failed downloads
FFMPEG_PATH = "ffmpeg"
BG_MUSIC_PATH = "assets/background_music.mp3"
BG_MUSIC_VOLUME = 0.12  # ~-18 dB under narration
TTS_LANG = "hi"  # gTTS language code (e.g. hi=Hindi, en=English)

# ──────────────────────────────────────────────────────────────────────
# Logging helpers
# ──────────────────────────────────────────────────────────────────────
logger = logging.getLogger("video_gen")


def setup_logging(log_dir: Path) -> None:
    """Configure console (INFO) + file (DEBUG) logging."""
    logger.setLevel(logging.DEBUG)

    fmt = logging.Formatter(
        "%(asctime)s  %(levelname)-8s  %(message)s", datefmt="%Y-%m-%d %H:%M:%S"
    )

    console = logging.StreamHandler(sys.stdout)
    console.setLevel(logging.INFO)
    console.setFormatter(fmt)
    logger.addHandler(console)

    log_file = log_dir / "generation.log"
    fh = logging.FileHandler(log_file, encoding="utf-8")
    fh.setLevel(logging.DEBUG)
    fh.setFormatter(fmt)
    logger.addHandler(fh)


# ──────────────────────────────────────────────────────────────────────
# Validation
# ──────────────────────────────────────────────────────────────────────
def load_cookies() -> dict[str, str]:
    """Load Meta AI cookies from environment / .env file.

    Required: META_AI_DATR, META_AI_ECTO_1_SESS
    Optional: META_AI_ABRA_SESS, META_AI_RD_CHALLENGE, META_AI_DPR, META_AI_WD
    """
    load_dotenv()

    required = {
        "datr": os.getenv("META_AI_DATR", ""),
        "ecto_1_sess": os.getenv("META_AI_ECTO_1_SESS", ""),
    }
    missing = [k for k, v in required.items() if not v]
    if missing:
        logger.error(
            "Missing required Meta AI cookies: %s. "
            "Set them in a .env file or as environment variables "
            "(META_AI_DATR, META_AI_ECTO_1_SESS).",
            ", ".join(missing),
        )
        sys.exit(1)

    cookies = dict(required)

    optional = {
        "abra_sess": os.getenv("META_AI_ABRA_SESS", ""),
        "rd_challenge": os.getenv("META_AI_RD_CHALLENGE", ""),
        "dpr": os.getenv("META_AI_DPR", ""),
        "wd": os.getenv("META_AI_WD", ""),
    }
    for key, val in optional.items():
        if val:
            cookies[key] = val

    logger.debug("Loaded cookies: %s", list(cookies.keys()))
    return cookies


def check_ffmpeg(ffmpeg_path: str) -> None:
    """Abort early if ffmpeg is not available."""
    if not shutil.which(ffmpeg_path):
        logger.error(
            "ffmpeg not found at '%s'. Install it or set FFMPEG_PATH.", ffmpeg_path
        )
        sys.exit(1)
    logger.debug("ffmpeg found: %s", shutil.which(ffmpeg_path))


# ──────────────────────────────────────────────────────────────────────
# Step A.5 — Reference image generation + upload
# ──────────────────────────────────────────────────────────────────────
def _pick_image_url(result: dict) -> str | None:
    """Extract the first usable image URL from any of the response shapes."""
    # 1. result["images"] — list of URLs or dicts
    for img in result.get("images", []):
        if isinstance(img, dict):
            url = img.get("url") or img.get("uri") or img.get("fallbackUrl")
        elif isinstance(img, str):
            url = img
        else:
            continue
        if url and url.startswith("http"):
            return url

    # 2. result["image_objects"] — might have resolved URLs
    for obj in result.get("image_objects", []):
        if isinstance(obj, dict):
            url = obj.get("url") or obj.get("fallbackUrl")
            if url and url.startswith("http"):
                return url

    # 3. result["image_urls"] — returned by generate_image_new()
    for url in result.get("image_urls", []):
        if isinstance(url, str) and url.startswith("http"):
            return url

    return None


def generate_reference_image(
    ai,
    character_prompt: str,
    output_dir: Path,
    max_retries: int = 3,
    retry_delay: int = 30,
) -> str | None:
    """Generate a character reference image and upload it to MetaAI.

    Uses ``generate_image_new()`` which wraps the low-level generation API
    with extra URL-resolution fallbacks (SSE polling + ``extract_media_urls``).

    Returns the media_id for use in image-to-video calls, or None on failure.
    """
    logger.info("Generating character reference image …")
    logger.debug("Character prompt: %s", character_prompt)

    image_path: Path | None = None

    for attempt in range(1, max_retries + 1):
        try:
            logger.info("  Image gen attempt %d/%d …", attempt, max_retries)

            # generate_image_new() has extra URL extraction on top of the
            # low-level generation_api.generate_image(). Pass longer polling
            # windows so the SDK waits for URLs to resolve.
            result = ai.generate_image_new(
                prompt=character_prompt,
                orientation="LANDSCAPE",
                max_attempts=40,
                wait_seconds=4,
            )

            # generate_image_new() wraps the raw response inside "response"
            image_url = _pick_image_url(result)
            if not image_url and isinstance(result.get("response"), dict):
                image_url = _pick_image_url(result["response"])

            if not image_url:
                logger.warning(
                    "  No image URL in response (attempt %d): %s",
                    attempt,
                    json.dumps(result, default=str)[:400],
                )
                if attempt < max_retries:
                    wait = retry_delay * (2 ** (attempt - 1))
                    logger.info("  Retrying in %ds …", wait)
                    time.sleep(wait)
                continue

            image_path = output_dir / "reference_characters.png"
            resp = requests.get(image_url, timeout=60)
            resp.raise_for_status()
            if len(resp.content) < 1024:
                logger.warning("  Downloaded image too small (%d bytes), retrying …", len(resp.content))
                if attempt < max_retries:
                    time.sleep(retry_delay)
                continue
            image_path.write_bytes(resp.content)
            logger.info(
                "  Reference image saved: %s (%.1f KB)",
                image_path.name,
                len(resp.content) / 1024,
            )
            break

        except Exception:
            logger.exception("  Image generation error (attempt %d)", attempt)
            if attempt < max_retries:
                wait = retry_delay * (2 ** (attempt - 1))
                logger.info("  Retrying in %ds …", wait)
                time.sleep(wait)

    if not image_path or not image_path.exists():
        logger.warning("Failed to generate reference image — proceeding without image-to-video.")
        return None

    # Upload the image to get a media_id
    try:
        logger.info("Uploading reference image to MetaAI …")
        upload_result = ai.upload_image(str(image_path))
        logger.debug("  Upload raw result: %s", upload_result)

        # upload_image() may return a dict like
        # {"success": True, "media_id": "12345", ...} or just the id string.
        if isinstance(upload_result, dict):
            media_id = upload_result.get("media_id") or upload_result.get("id")
        else:
            media_id = str(upload_result) if upload_result else None

        if not media_id:
            logger.warning("Upload succeeded but no media_id found in response — skipping image-to-video.")
            return None

        media_id = str(media_id)
        logger.info("  Upload successful — media_id: %s", media_id)
        return media_id
    except Exception:
        logger.exception("Failed to upload reference image — proceeding without image-to-video.")
        return None


# ──────────────────────────────────────────────────────────────────────
# Step B — Video generation via MetaAI
# ──────────────────────────────────────────────────────────────────────
def _extract_download_urls(api_result: dict) -> list[str]:
    """Collect all unique downloadable CDN URLs from a GenerationAPI response."""
    seen: set[str] = set()
    ordered: list[str] = []

    def add(u: str | None) -> None:
        if not u or not isinstance(u, str) or not u.startswith("http"):
            return
        if u not in seen:
            seen.add(u)
            ordered.append(u)

    for vid in api_result.get("videos", []):
        if isinstance(vid, dict):
            add(vid.get("url"))
            add(vid.get("fallbackUrl"))
        elif isinstance(vid, str):
            add(vid)

    for vid in api_result.get("video_objects", []):
        if isinstance(vid, dict):
            for key in ("url", "fallbackUrl"):
                u = vid.get(key)
                if u and isinstance(u, str) and u.startswith("http") and "fbcdn" in u:
                    add(u)

    return ordered


def _extract_download_url(api_result: dict) -> str | None:
    """First downloadable CDN URL (backward compatibility)."""
    urls = _extract_download_urls(api_result)
    return urls[0] if urls else None


def _shorten_description(desc: str, max_words: int = 15) -> str:
    """Take the first N words of a character description."""
    words = desc.split()
    if len(words) <= max_words:
        return desc.rstrip(".")
    return " ".join(words[:max_words]).rstrip(",.")


def _build_prompt_with_characters(
    video_prompt: str, characters: dict[str, str]
) -> str:
    """Prepend short character cues to a scene's video prompt.

    Keeps the combined prompt at a reasonable length so MetaAI doesn't
    choke on an oversized input.
    """
    if not characters:
        return video_prompt

    char_lines = ". ".join(
        _shorten_description(desc) for desc in characters.values()
    )
    return f"{char_lines}. {video_prompt}"


def generate_scene_videos(
    scenes: list[dict],
    cookies: dict[str, str],
    orientation: str,
    rate_limit: int,
    max_retries: int,
    retry_delay: int,
    ref_media_id: str | None = None,
    characters: dict[str, str] | None = None,
) -> list[dict]:
    """
    Call MetaAI for each scene prompt.  Returns a list of result dicts:
      [{"scene_number": int, "url": str|None, "status": "success"|"failed"}, ...]
    """
    from metaai_api import MetaAI

    ai = MetaAI(cookies=cookies)
    results: list[dict] = []

    for idx, scene in enumerate(scenes):
        num = scene["scene_number"]
        prompt = _build_prompt_with_characters(
            scene["video_prompt"], characters or {}
        )
        logger.info(
            "Scene %d/%d — %s", num, len(scenes), scene["description"]
        )
        logger.debug("Prompt: %s", prompt)

        url: str | None = None
        all_urls: list[str] = []
        for attempt in range(1, max_retries + 1):
            try:
                logger.info("  Attempt %d/%d …", attempt, max_retries)
                gen_kwargs: dict = {"prompt": prompt, "fetch_urls": True}
                if ref_media_id:
                    gen_kwargs["media_ids"] = [ref_media_id]
                api_result = ai.generation_api.generate_video(**gen_kwargs)
                found = _extract_download_urls(api_result)
                if found:
                    url = found[0]
                    all_urls = found
                    if len(found) > 1:
                        logger.info(
                            "  Success — %d candidate URL(s), first: %s",
                            len(found),
                            url[:80],
                        )
                    else:
                        logger.info("  Success — %s", url[:80])
                    break
                logger.warning("  API returned no downloadable video URLs.")
            except Exception:
                logger.exception("  API error on attempt %d", attempt)

            if attempt < max_retries:
                wait = retry_delay * (2 ** (attempt - 1))
                logger.info("  Retrying in %ds …", wait)
                time.sleep(wait)

        if url and not all_urls:
            all_urls = [url]
        results.append(
            {
                "scene_number": num,
                "url": url,
                "urls": all_urls,
                "status": "success" if url else "failed",
            }
        )

        if idx < len(scenes) - 1:
            logger.debug("Rate-limit pause: %ds", rate_limit)
            time.sleep(rate_limit)

    return results


# ──────────────────────────────────────────────────────────────────────
# Step C — Download videos
# ──────────────────────────────────────────────────────────────────────
def _scene_video_path(scene_number: int, output_dir: Path) -> Path:
    return output_dir / f"scene_{scene_number:03d}.mp4"


def clip_file_valid(path: Path) -> bool:
    """True if a clip exists and is large enough to be a real video."""
    try:
        return path.exists() and path.stat().st_size >= MIN_CLIP_BYTES
    except OSError:
        return False


def scenes_missing_clips(scenes: list[dict], output_dir: Path) -> list[dict]:
    """Scenes that have no valid ``scene_NNN.mp4`` on disk."""
    return [
        s
        for s in scenes
        if not clip_file_valid(_scene_video_path(s["scene_number"], output_dir))
    ]


def ordered_scene_clip_paths(story: dict, output_dir: Path) -> list[Path]:
    """Downloaded scene videos in story order (skips scenes still missing)."""
    clips: list[Path] = []
    for scene in story["scenes"]:
        p = _scene_video_path(scene["scene_number"], output_dir)
        if clip_file_valid(p):
            clips.append(p)
    return clips


def merge_generation_into_results(
    results: list[dict], retry_batch: list[dict]
) -> None:
    """Update ``results`` when a recovery pass returns a successful generation."""
    by_num = {r["scene_number"]: i for i, r in enumerate(results)}
    for nr in retry_batch:
        if nr["status"] != "success":
            continue
        idx = by_num.get(nr["scene_number"])
        if idx is not None:
            results[idx] = nr


def download_videos(
    results: list[dict],
    output_dir: Path,
    attempts_per_url: int = DOWNLOAD_ATTEMPTS_PER_URL,
) -> list[Path]:
    """Download each successful scene. Tries every CDN URL until one works."""
    downloaded: list[Path] = []

    for r in results:
        if r["status"] != "success":
            logger.warning(
                "Skipping scene %d (generation failed).", r["scene_number"]
            )
            continue

        candidate_urls: list[str] = list(r.get("urls") or [])
        if r.get("url") and r["url"] not in candidate_urls:
            candidate_urls.insert(0, r["url"])
        elif not candidate_urls and r.get("url"):
            candidate_urls = [r["url"]]

        if not candidate_urls:
            logger.warning("Scene %d: no URLs to download.", r["scene_number"])
            continue

        filename = f"scene_{r['scene_number']:03d}.mp4"
        dest = output_dir / filename
        saved = False

        for url_idx, video_url in enumerate(candidate_urls):
            for attempt in range(attempts_per_url):
                try:
                    logger.info(
                        "Downloading scene %d → %s (URL %d/%d, attempt %d/%d)",
                        r["scene_number"],
                        filename,
                        url_idx + 1,
                        len(candidate_urls),
                        attempt + 1,
                        attempts_per_url,
                    )
                    resp = requests.get(video_url, stream=True, timeout=180)
                    resp.raise_for_status()
                    with open(dest, "wb") as f:
                        for chunk in resp.iter_content(chunk_size=1024 * 256):
                            f.write(chunk)

                    size = dest.stat().st_size
                    if size < MIN_CLIP_BYTES:
                        logger.warning(
                            "  File too small (%d bytes); trying next URL/attempt …",
                            size,
                        )
                        dest.unlink(missing_ok=True)
                        continue

                    logger.info("  Saved %s (%.2f MB)", filename, size / 1024 / 1024)
                    downloaded.append(dest)
                    saved = True
                    break
                except Exception:
                    logger.exception(
                        "  Download error scene %d (URL %d, attempt %d)",
                        r["scene_number"],
                        url_idx + 1,
                        attempt + 1,
                    )
                    dest.unlink(missing_ok=True)
            if saved:
                break

        if not saved:
            logger.error(
                "  Failed to download scene %d after all URLs and retries.",
                r["scene_number"],
            )

    return downloaded


def run_failed_scene_recovery(
    story: dict,
    results: list[dict],
    output_dir: Path,
    cookies: dict[str, str],
    orientation: str,
    rate_limit: int,
    max_retries: int,
    retry_delay: int,
    ref_media_id: str | None,
    characters: dict[str, str] | None,
    extra_passes: int,
) -> None:
    """Re-download and/or regenerate until clips exist or passes are exhausted."""
    for pass_num in range(extra_passes):
        missing = scenes_missing_clips(story["scenes"], output_dir)
        if not missing:
            logger.info("All scene clips present after recovery.")
            return

        missing_nums = {s["scene_number"] for s in missing}

        redownload = [
            r
            for r in results
            if r["scene_number"] in missing_nums
            and r["status"] == "success"
            and (r.get("urls") or r.get("url"))
        ]
        if redownload:
            logger.info(
                "Recovery pass %d/%d: re-downloading %d scene(s) that still lack a valid file …",
                pass_num + 1,
                extra_passes,
                len(redownload),
            )
            download_videos(redownload, output_dir)
            time.sleep(min(rate_limit, 8))

        missing = scenes_missing_clips(story["scenes"], output_dir)
        if not missing:
            return

        logger.info(
            "Recovery pass %d/%d: regenerating %d scene(s) still missing clips …",
            pass_num + 1,
            extra_passes,
            len(missing),
        )
        time.sleep(rate_limit)
        retry_results = generate_scene_videos(
            scenes=missing,
            cookies=cookies,
            orientation=orientation,
            rate_limit=rate_limit,
            max_retries=max_retries,
            retry_delay=retry_delay,
            ref_media_id=ref_media_id,
            characters=characters,
        )
        merge_generation_into_results(results, retry_results)
        download_videos(
            [r for r in retry_results if r["status"] == "success"],
            output_dir,
        )


# ──────────────────────────────────────────────────────────────────────
# Step C.5 — Generate narration audio via gTTS
# ──────────────────────────────────────────────────────────────────────
def _text_has_devanagari(text: str) -> bool:
    """True if text contains Devanagari script (typical for Hindi)."""
    return any("\u0900" <= c <= "\u097f" for c in text)


def _prepare_tts_text(
    text: str,
    tts_lang: str,
    translate_from_en: bool,
) -> str:
    """Optionally translate English story text to Hindi before Hindi TTS."""
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
        logger.warning(
            "English→Hindi translation failed (%s). "
            "Install deep-translator (`pip install deep-translator`) or add Hindi "
            "narration in stories.py / use --no-translate-narration with Devanagari text.",
            exc,
        )
        return text


def generate_narration_audio(
    story: dict,
    output_dir: Path,
    tts_lang: str = TTS_LANG,
    translate_to_hi: bool = True,
) -> list[Path]:
    """Generate MP3 narration files for intro, each scene, and outro.

    For ``tts_lang=\"hi\"``, English narration in ``stories.py`` is translated
    to Hindi before synthesis unless ``translate_to_hi`` is False or the text
    already contains Devanagari.

    Returns an ordered list of audio file paths (intro, scene_001, …, outro).
    """
    from gtts import gTTS

    audio_files: list[Path] = []
    translate = translate_to_hi and tts_lang == "hi"

    # Intro narration
    intro_text = story.get("narrator_intro", "")
    if intro_text:
        intro_path = output_dir / "narration_intro.mp3"
        logger.info("Generating intro narration (%s) …", tts_lang)
        spoken = _prepare_tts_text(intro_text, tts_lang, translate)
        tts = gTTS(text=spoken, lang=tts_lang, slow=False)
        tts.save(str(intro_path))
        audio_files.append(intro_path)
        logger.info("  Saved %s", intro_path.name)

    # Per-scene narration
    for scene in story["scenes"]:
        narration = scene.get("narration", "")
        if not narration:
            logger.warning("  Scene %d has no narration text — skipping.", scene["scene_number"])
            continue

        audio_path = output_dir / f"narration_{scene['scene_number']:03d}.mp3"
        logger.info("Generating narration for scene %d (%s) …", scene["scene_number"], tts_lang)
        spoken = _prepare_tts_text(narration, tts_lang, translate)
        tts = gTTS(text=spoken, lang=tts_lang, slow=False)
        tts.save(str(audio_path))
        audio_files.append(audio_path)
        logger.debug("  Saved %s", audio_path.name)

    # Outro narration
    outro_text = story.get("narrator_outro", "")
    if outro_text:
        outro_path = output_dir / "narration_outro.mp3"
        logger.info("Generating outro narration (%s) …", tts_lang)
        spoken = _prepare_tts_text(outro_text, tts_lang, translate)
        tts = gTTS(text=spoken, lang=tts_lang, slow=False)
        tts.save(str(outro_path))
        audio_files.append(outro_path)
        logger.info("  Saved %s", outro_path.name)

    logger.info("Generated %d narration audio files.", len(audio_files))
    return audio_files


# ──────────────────────────────────────────────────────────────────────
# Step C.7 — Per-scene composition (video + narration)
# ──────────────────────────────────────────────────────────────────────
def _get_audio_duration(audio_path: Path, ffmpeg_path: str) -> float:
    """Get duration of an audio file in seconds via ffprobe."""
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
        logger.warning("Could not determine duration for %s, defaulting to 10s", audio_path)
        return 10.0


def compose_scenes_with_narration(
    video_clips: list[Path],
    story: dict,
    output_dir: Path,
    ffmpeg_path: str,
) -> list[Path]:
    """Combine each video clip with its matching narration audio.

    Loops the video if the narration is longer. Returns ordered list of
    narrated clip paths.
    """
    narrated_clips: list[Path] = []

    intro_narration = output_dir / "narration_intro.mp3"
    outro_narration = output_dir / "narration_outro.mp3"

    # Map scene numbers to video files
    clip_by_scene: dict[int, Path] = {}
    for clip in video_clips:
        try:
            scene_num = int(clip.stem.split("_")[1])
            clip_by_scene[scene_num] = clip
        except (IndexError, ValueError):
            continue

    # Compose intro: use first scene's video with intro narration
    if intro_narration.exists() and clip_by_scene:
        first_scene_num = min(clip_by_scene.keys())
        first_clip = clip_by_scene[first_scene_num]
        intro_out = output_dir / "composed_intro.mp4"

        duration = _get_audio_duration(intro_narration, ffmpeg_path)
        logger.info("Composing intro (%.1fs narration) with scene %d video …", duration, first_scene_num)

        cmd = [
            ffmpeg_path, "-y",
            "-stream_loop", "-1", "-i", str(first_clip),
            "-i", str(intro_narration),
            "-map", "0:v", "-map", "1:a",
            "-c:v", "libx264", "-preset", "medium", "-crf", "23",
            "-c:a", "aac", "-b:a", "128k",
            "-shortest", "-movflags", "+faststart",
            str(intro_out),
        ]
        proc = subprocess.run(cmd, capture_output=True, text=True)
        if proc.returncode == 0 and intro_out.exists():
            narrated_clips.append(intro_out)
            logger.info("  Composed intro → %s", intro_out.name)
        else:
            logger.warning("  Intro composition failed: %s", proc.stderr[-500:] if proc.stderr else "")

    # Compose each scene
    for scene in story["scenes"]:
        num = scene["scene_number"]
        clip = clip_by_scene.get(num)
        narration_path = output_dir / f"narration_{num:03d}.mp3"

        if not clip or not clip.exists():
            logger.warning("No video clip for scene %d — skipping composition.", num)
            continue

        out_path = output_dir / f"composed_{num:03d}.mp4"

        if narration_path.exists():
            duration = _get_audio_duration(narration_path, ffmpeg_path)
            logger.info("Composing scene %d (%.1fs narration) …", num, duration)

            cmd = [
                ffmpeg_path, "-y",
                "-stream_loop", "-1", "-i", str(clip),
                "-i", str(narration_path),
                "-map", "0:v", "-map", "1:a",
                "-c:v", "libx264", "-preset", "medium", "-crf", "23",
                "-c:a", "aac", "-b:a", "128k",
                "-shortest", "-movflags", "+faststart",
                str(out_path),
            ]
        else:
            logger.info("Composing scene %d (no narration — video only) …", num)
            cmd = [
                ffmpeg_path, "-y",
                "-i", str(clip),
                "-c:v", "libx264", "-preset", "medium", "-crf", "23",
                "-an", "-movflags", "+faststart",
                str(out_path),
            ]

        proc = subprocess.run(cmd, capture_output=True, text=True)
        if proc.returncode == 0 and out_path.exists():
            narrated_clips.append(out_path)
            logger.debug("  Composed scene %d → %s", num, out_path.name)
        else:
            logger.warning("  Composition failed for scene %d: %s", num, proc.stderr[-500:] if proc.stderr else "")

    # Compose outro: use last scene's video with outro narration
    if outro_narration.exists() and clip_by_scene:
        last_scene_num = max(clip_by_scene.keys())
        last_clip = clip_by_scene[last_scene_num]
        outro_out = output_dir / "composed_outro.mp4"

        duration = _get_audio_duration(outro_narration, ffmpeg_path)
        logger.info("Composing outro (%.1fs narration) with scene %d video …", duration, last_scene_num)

        cmd = [
            ffmpeg_path, "-y",
            "-stream_loop", "-1", "-i", str(last_clip),
            "-i", str(outro_narration),
            "-map", "0:v", "-map", "1:a",
            "-c:v", "libx264", "-preset", "medium", "-crf", "23",
            "-c:a", "aac", "-b:a", "128k",
            "-shortest", "-movflags", "+faststart",
            str(outro_out),
        ]
        proc = subprocess.run(cmd, capture_output=True, text=True)
        if proc.returncode == 0 and outro_out.exists():
            narrated_clips.append(outro_out)
            logger.info("  Composed outro → %s", outro_out.name)
        else:
            logger.warning("  Outro composition failed: %s", proc.stderr[-500:] if proc.stderr else "")

    logger.info("Composed %d narrated clips total.", len(narrated_clips))
    return narrated_clips


# ──────────────────────────────────────────────────────────────────────
# Step D — Merge with FFmpeg
# ──────────────────────────────────────────────────────────────────────
def merge_videos(
    clips: list[Path], output_dir: Path, ffmpeg_path: str
) -> Path | None:
    """Concatenate clips into a single MP4.  Returns path to the final file."""
    if not clips:
        logger.error("No clips to merge.")
        return None

    filelist = output_dir / "filelist.txt"
    with open(filelist, "w") as f:
        for clip in clips:
            f.write(f"file '{clip.resolve()}'\n")

    final = output_dir / "final_video.mp4"

    cmd_copy = [
        ffmpeg_path,
        "-y",
        "-f", "concat",
        "-safe", "0",
        "-i", str(filelist),
        "-c", "copy",
        "-movflags", "+faststart",
        str(final),
    ]
    logger.info("Merging %d clips (stream-copy) …", len(clips))
    logger.debug("Command: %s", " ".join(cmd_copy))
    proc = subprocess.run(cmd_copy, capture_output=True, text=True)

    if proc.returncode == 0 and final.exists() and final.stat().st_size > 0:
        logger.info("Merge complete (stream-copy): %s", final)
        return final

    logger.warning("Stream-copy merge failed — falling back to re-encode.")
    logger.debug("ffmpeg stderr: %s", proc.stderr[-2000:] if proc.stderr else "")

    cmd_reencode = [
        ffmpeg_path,
        "-y",
        "-f", "concat",
        "-safe", "0",
        "-i", str(filelist),
        "-c:v", "libx264",
        "-preset", "medium",
        "-crf", "23",
        "-c:a", "aac",
        "-b:a", "128k",
        "-movflags", "+faststart",
        str(final),
    ]
    logger.info("Re-encoding %d clips …", len(clips))
    proc2 = subprocess.run(cmd_reencode, capture_output=True, text=True)

    if proc2.returncode == 0 and final.exists() and final.stat().st_size > 0:
        logger.info("Merge complete (re-encoded): %s", final)
        return final

    logger.error("All merge strategies failed: %s", proc2.stderr[-2000:] if proc2.stderr else "")
    return None


# ──────────────────────────────────────────────────────────────────────
# Step D.5 — Mix background music into final video
# ──────────────────────────────────────────────────────────────────────
def mix_background_music(
    video_path: Path,
    output_dir: Path,
    ffmpeg_path: str,
    bg_music_path: str = BG_MUSIC_PATH,
    volume: float = BG_MUSIC_VOLUME,
) -> Path:
    """Layer background music under the narrated video at low volume.

    Returns the path to the final output (original if mixing fails or no music found).
    """
    music_file = Path(bg_music_path)
    if not music_file.exists():
        logger.info("No background music file at %s — skipping music mix.", bg_music_path)
        return video_path

    final_with_music = output_dir / "final_video_with_music.mp4"

    filter_complex = (
        f"[1:a]volume={volume},aloop=loop=-1:size=2e+09[bg];"
        f"[0:a][bg]amix=inputs=2:duration=first[aout]"
    )

    cmd = [
        ffmpeg_path, "-y",
        "-i", str(video_path),
        "-i", str(music_file),
        "-filter_complex", filter_complex,
        "-map", "0:v", "-map", "[aout]",
        "-c:v", "copy",
        "-c:a", "aac", "-b:a", "128k",
        "-movflags", "+faststart",
        str(final_with_music),
    ]
    logger.info("Mixing background music (volume=%.2f) …", volume)
    logger.debug("Command: %s", " ".join(cmd))
    proc = subprocess.run(cmd, capture_output=True, text=True)

    if proc.returncode == 0 and final_with_music.exists() and final_with_music.stat().st_size > 0:
        logger.info("Background music mixed → %s", final_with_music.name)
        # Replace the non-music version
        final_output = output_dir / "final_video.mp4"
        video_path.unlink(missing_ok=True)
        final_with_music.rename(final_output)
        return final_output

    logger.warning("Background music mixing failed — keeping narration-only version.")
    logger.debug("ffmpeg stderr: %s", proc.stderr[-1000:] if proc.stderr else "")
    return video_path


# ──────────────────────────────────────────────────────────────────────
# CLI & main
# ──────────────────────────────────────────────────────────────────────
def parse_args() -> argparse.Namespace:
    load_dotenv()
    parser = argparse.ArgumentParser(
        description="Generate a video from a Panchatantra story using MetaAI."
    )
    parser.add_argument(
        "--story",
        default=STORY_SLUG,
        help=f"Story slug to generate (default: {STORY_SLUG})",
    )
    parser.add_argument(
        "--list-stories",
        action="store_true",
        help="List available stories and exit.",
    )
    parser.add_argument(
        "--output-dir",
        default=OUTPUT_DIR,
        help=f"Base output directory (default: {OUTPUT_DIR})",
    )
    parser.add_argument(
        "--orientation",
        default=VIDEO_ORIENTATION,
        choices=["LANDSCAPE", "VERTICAL", "SQUARE"],
        help=f"Video orientation (default: {VIDEO_ORIENTATION})",
    )
    parser.add_argument(
        "--rate-limit",
        type=int,
        default=RATE_LIMIT_SECONDS,
        help=f"Seconds between API calls (default: {RATE_LIMIT_SECONDS})",
    )
    parser.add_argument(
        "--max-retries",
        type=int,
        default=MAX_RETRIES,
        help=f"Max retries per failed scene (default: {MAX_RETRIES})",
    )
    parser.add_argument(
        "--retry-delay",
        type=int,
        default=RETRY_DELAY,
        help=f"Base retry delay in seconds (default: {RETRY_DELAY})",
    )
    parser.add_argument(
        "--ffmpeg",
        default=FFMPEG_PATH,
        help=f"Path to ffmpeg binary (default: {FFMPEG_PATH})",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Validate config and print scene prompts without calling the API.",
    )
    parser.add_argument(
        "--cleanup",
        action="store_true",
        help="Delete individual scene clips after successful merge.",
    )
    parser.add_argument(
        "--no-audio",
        action="store_true",
        help="Skip narration generation and background music (video-only output).",
    )
    parser.add_argument(
        "--bg-music",
        default=BG_MUSIC_PATH,
        help=f"Path to background music MP3 (default: {BG_MUSIC_PATH})",
    )
    parser.add_argument(
        "--tts-lang",
        default=os.getenv("VIDEO_TTS_LANG", TTS_LANG),
        help=(
            "gTTS language code: hi (Hindi, default), en, etc. "
            "Override with env VIDEO_TTS_LANG."
        ),
    )
    parser.add_argument(
        "--no-translate-narration",
        action="store_true",
        help=(
            "With Hindi TTS: skip English→Hindi translation (use when narration "
            "in stories.py is already written in Devanagari)."
        ),
    )
    parser.add_argument(
        "--failed-scene-passes",
        type=int,
        default=FAILED_SCENE_EXTRA_PASSES,
        help=(
            "After the main run, extra rounds of re-download and optional re-generation "
            "for scenes with missing or corrupt clips (default: %(default)s)."
        ),
    )
    return parser.parse_args()


def print_summary(
    story_title: str,
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
    logger.info("  Story:      %s", story_title)
    logger.info("  Scenes:     %d total, %d succeeded, %d failed", len(results), success, failed)
    if audio_enabled and tts_lang:
        logger.info("  Audio:      enabled (TTS lang=%s, narration + music)", tts_lang)
    elif audio_enabled:
        logger.info("  Audio:      enabled (narration + music)")
    else:
        logger.info("  Audio:      disabled")
    logger.info("  Output dir: %s", run_dir)
    if final_path:
        size_mb = final_path.stat().st_size / 1024 / 1024
        logger.info("  Final video: %s (%.2f MB)", final_path.name, size_mb)
    else:
        logger.info("  Final video: NONE (merge failed or no clips)")
    logger.info("  Elapsed:    %.1f seconds", elapsed)
    logger.info("=" * 60)


def main() -> None:
    args = parse_args()

    # --list-stories
    if args.list_stories:
        print("\nAvailable stories:\n")
        for slug, title in list_stories():
            print(f"  {slug:30s}  {title}")
        print()
        return

    # Load story
    story = get_story(args.story)
    if story is None:
        available = ", ".join(s for s, _ in list_stories())
        print(f"Error: unknown story '{args.story}'. Available: {available}")
        sys.exit(1)

    # Create output directory
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    run_dir = Path(args.output_dir) / f"{args.story}_{timestamp}"
    run_dir.mkdir(parents=True, exist_ok=True)

    setup_logging(run_dir)
    logger.info("Story: %s — \"%s\"", args.story, story["title"])
    logger.info("Scenes: %d", len(story["scenes"]))
    logger.info("Audio: %s", "disabled (--no-audio)" if args.no_audio else "enabled")
    if not args.no_audio:
        logger.info("TTS language: %s", args.tts_lang)
        if args.tts_lang == "hi" and not args.no_translate_narration:
            logger.info("Narration: English→Hindi translation before TTS (if text is not Devanagari)")
        elif args.tts_lang == "hi":
            logger.info("Narration: no translation (--no-translate-narration); expect Hindi script in stories")
    logger.info("Output: %s", run_dir)

    # --dry-run
    if args.dry_run:
        logger.info("DRY RUN — validating configuration and printing prompts.\n")

        if shutil.which(args.ffmpeg):
            logger.info("ffmpeg: OK (%s)", shutil.which(args.ffmpeg))
        else:
            logger.warning("ffmpeg: NOT FOUND at '%s'", args.ffmpeg)

        load_dotenv()
        for var, required in [
            ("META_AI_DATR", True),
            ("META_AI_ECTO_1_SESS", True),
            ("META_AI_ABRA_SESS", False),
            ("META_AI_RD_CHALLENGE", False),
        ]:
            val = os.getenv(var, "")
            if val:
                logger.info("Cookie %s: OK", var)
            elif required:
                logger.warning("Cookie %s: MISSING (required)", var)
            else:
                logger.info("Cookie %s: not set (optional)", var)

        if story.get("character_prompt"):
            logger.info("\nCharacter reference prompt: %s", story["character_prompt"])
        if story.get("characters"):
            logger.info("\nCharacter descriptions:")
            for name, desc in story["characters"].items():
                logger.info("  %s: %s", name, desc[:80])

        logger.info("\n--- Scene Prompts ---\n")
        for scene in story["scenes"]:
            logger.info(
                "Scene %d: %s (~%ds)",
                scene["scene_number"],
                scene["description"],
                scene["duration_hint"],
            )
            logger.info("  Prompt:    %s", scene["video_prompt"][:120] + "…")
            if scene.get("narration"):
                logger.info("  Narration: %s", scene["narration"][:120] + "…")
            logger.info("")

        total_hint = sum(s["duration_hint"] for s in story["scenes"])
        logger.info("Estimated video length: ~%ds (%.1f min)", total_hint, total_hint / 60)

        bg_path = Path(args.bg_music)
        if bg_path.exists():
            logger.info("Background music: %s (found)", bg_path)
        else:
            logger.info("Background music: %s (not found — will be skipped)", bg_path)

        if not args.no_audio:
            logger.info("TTS language: %s", args.tts_lang)
            logger.info(
                "Translate narration to Hindi: %s",
                "no (--no-translate-narration)" if args.no_translate_narration else "yes (when using Hindi TTS and Latin text)",
            )

        logger.info("Dry run complete.")
        return

    # Full run
    check_ffmpeg(args.ffmpeg)
    cookies = load_cookies()

    t_start = time.time()

    try:
        # Step A.5 — generate + upload character reference image
        from metaai_api import MetaAI

        ai = MetaAI(cookies=cookies)
        ref_media_id: str | None = None

        character_prompt = story.get("character_prompt", "")
        if character_prompt:
            ref_media_id = generate_reference_image(
                ai=ai,
                character_prompt=character_prompt,
                output_dir=run_dir,
                max_retries=args.max_retries,
                retry_delay=args.retry_delay,
            )

        # Step B — generate scene videos (with image-to-video if ref available)
        results = generate_scene_videos(
            scenes=story["scenes"],
            cookies=cookies,
            orientation=args.orientation,
            rate_limit=args.rate_limit,
            max_retries=args.max_retries,
            retry_delay=args.retry_delay,
            ref_media_id=ref_media_id,
            characters=story.get("characters"),
        )

        # Step C — download (+ recovery for failed / partial downloads)
        download_videos(results, run_dir)
        run_failed_scene_recovery(
            story=story,
            results=results,
            output_dir=run_dir,
            cookies=cookies,
            orientation=args.orientation,
            rate_limit=args.rate_limit,
            max_retries=args.max_retries,
            retry_delay=args.retry_delay,
            ref_media_id=ref_media_id,
            characters=story.get("characters"),
            extra_passes=args.failed_scene_passes,
        )
        clips = ordered_scene_clip_paths(story, run_dir)

        if not args.no_audio:
            # Step C.5 — generate narration audio
            generate_narration_audio(
                story,
                run_dir,
                tts_lang=args.tts_lang,
                translate_to_hi=not args.no_translate_narration,
            )

            # Step C.7 — compose each scene with narration
            narrated_clips = compose_scenes_with_narration(
                video_clips=clips,
                story=story,
                output_dir=run_dir,
                ffmpeg_path=args.ffmpeg,
            )
            merge_input = narrated_clips if narrated_clips else clips
        else:
            merge_input = clips

        # Step D — merge
        final_path = merge_videos(merge_input, run_dir, args.ffmpeg)

        # Step D.5 — mix background music (only if audio is enabled)
        if final_path and not args.no_audio:
            final_path = mix_background_music(
                video_path=final_path,
                output_dir=run_dir,
                ffmpeg_path=args.ffmpeg,
                bg_music_path=args.bg_music,
            )

        # Cleanup
        if args.cleanup and final_path:
            logger.info("Cleaning up individual clips …")
            for clip in clips:
                clip.unlink(missing_ok=True)
            for p in run_dir.glob("composed_*.mp4"):
                p.unlink(missing_ok=True)
            for p in run_dir.glob("narration_*.mp3"):
                p.unlink(missing_ok=True)
            filelist = run_dir / "filelist.txt"
            filelist.unlink(missing_ok=True)

    except KeyboardInterrupt:
        logger.warning("Interrupted! Attempting to merge available clips …")
        existing = sorted(run_dir.glob("scene_*.mp4"))
        if existing:
            final_path = merge_videos(existing, run_dir, args.ffmpeg)
        else:
            final_path = None
        results = []

    elapsed = time.time() - t_start
    print_summary(
        story["title"],
        results,
        final_path,
        run_dir,
        elapsed,
        not args.no_audio,
        tts_lang=args.tts_lang if not args.no_audio else None,
    )


if __name__ == "__main__":
    main()
