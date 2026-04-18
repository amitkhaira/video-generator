#!/usr/bin/env python3
"""Stage 05 — Video Clip Generator (provider-agnostic).

Iterates output/<topic>/video_prompts.json and calls the configured video
provider for each prompt. Saves clips to output/<topic>/clips/NNNN.mp4
with a manifest for resume.

INPUT:
    output/<topic>/video_prompts.json   — from stage 04
OUTPUT:
    output/<topic>/clips/<beat_id>_<clip_index>.mp4
    output/<topic>/clips/manifest.json
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
import time
from pathlib import Path

import config
from video_providers import get_provider
from utils.ffprobe import probe_duration

logger = logging.getLogger("cosmic_docs.stage05")


def _setup_logging() -> None:
    logger.setLevel(logging.DEBUG)
    fmt = logging.Formatter("%(asctime)s  %(levelname)-7s  %(message)s", "%H:%M:%S")
    console = logging.StreamHandler(sys.stdout)
    console.setLevel(logging.INFO)
    console.setFormatter(fmt)
    logger.addHandler(console)


def _clip_filename(beat_id: int, clip_index: int) -> str:
    return f"{beat_id:03d}_{clip_index:02d}.mp4"


def _clip_valid(path: Path) -> bool:
    try:
        return path.is_file() and path.stat().st_size >= config.MIN_CLIP_BYTES
    except OSError:
        return False


def _test_prompts() -> list[dict]:
    """3-clip smoke-test prompts covering different shot archetypes."""
    return [
        {
            "beat_id": 0, "clip_index": 0, "duration_sec": 5.0,
            "prompt": (
                "Vast cosmic vista, swirling spiral galaxy, billions of stars, deep space, "
                "tiny Earth-like planet in foreground, slow zoom in, cinematic 16:9, "
                "deep cosmic blue shadows + warm gold highlights, high contrast, filmic grain, 5s"
            ),
            "aspect_ratio": "16:9", "continuation_of": None,
        },
        {
            "beat_id": 0, "clip_index": 1, "duration_sec": 5.0,
            "prompt": (
                "Weathered sandstone temple at golden hour, intricate carved reliefs glowing in warm gold, "
                "mysterious symbols, cinematic wide shot 16:9, slow dolly push, deep cosmic blue shadows, "
                "atmospheric dust particles, high contrast, filmic grain, 5s"
            ),
            "aspect_ratio": "16:9", "continuation_of": None,
        },
        {
            "beat_id": 0, "clip_index": 2, "duration_sec": 5.0,
            "prompt": (
                "Silhouette of meditating sage on mountaintop, long white beard, aura of golden light, "
                "deep blue night sky with visible galaxy, cinematic 16:9, slow reveal, "
                "deep cosmic blue shadows + warm gold highlights, high contrast, filmic grain, 5s"
            ),
            "aspect_ratio": "16:9", "continuation_of": None,
        },
    ]


def _load_manifest(path: Path) -> dict:
    if path.exists():
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            pass
    return {"clips": []}


def _save_manifest(path: Path, manifest: dict) -> None:
    path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")


def _parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Stage 05 — Video Clip Generator")
    parser.add_argument("--limit", type=int, default=None, help="process only first N clips")
    parser.add_argument("--force", action="store_true", help="regenerate existing clips")
    parser.add_argument(
        "--test-prompts", action="store_true",
        help="run 3 smoke-test prompts into output/_test_clips/ and exit",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    _setup_logging()
    args = _parse_args(argv if argv is not None else sys.argv[1:])

    base_dir = Path(__file__).resolve().parent

    if args.test_prompts:
        out_dir = base_dir / "output" / "_test_clips"
        out_dir.mkdir(parents=True, exist_ok=True)
        provider = get_provider(config.VIDEO_PROVIDER)
        for i, p in enumerate(_test_prompts(), start=1):
            out = out_dir / f"test_{i:02d}.mp4"
            logger.info("[test %d/3] %s", i, config.VIDEO_PROVIDER)
            provider.generate(p["prompt"], p["duration_sec"], out)
        logger.info("Test clips in %s", out_dir)
        return 0

    output_dir = Path(config.output_dir_path())
    clips_dir = Path(config.clips_dir_path())
    clips_dir.mkdir(parents=True, exist_ok=True)

    prompts_path = output_dir / "video_prompts.json"
    if not prompts_path.exists():
        logger.error("video_prompts.json missing — run 04 first (%s)", prompts_path)
        return 2

    prompts_payload = json.loads(prompts_path.read_text(encoding="utf-8"))
    prompts = prompts_payload["prompts"]
    if args.limit:
        prompts = prompts[: args.limit]

    provider = get_provider(config.VIDEO_PROVIDER)
    logger.info(
        "Video provider=%s MAX_CLIP_SEC=%d clips_to_gen=%d",
        config.VIDEO_PROVIDER, provider.MAX_CLIP_SEC, len(prompts),
    )

    manifest_path = clips_dir / "manifest.json"
    manifest = _load_manifest(manifest_path)
    manifest_index = {(c["beat_id"], c["clip_index"]): c for c in manifest["clips"]}

    for idx, prompt_entry in enumerate(prompts, start=1):
        beat_id = prompt_entry["beat_id"]
        clip_idx = prompt_entry["clip_index"]
        duration = prompt_entry["duration_sec"]
        out_path = clips_dir / _clip_filename(beat_id, clip_idx)

        if _clip_valid(out_path) and not args.force:
            logger.info(
                "[%d/%d] skip beat=%03d idx=%02d (%s)",
                idx, len(prompts), beat_id, clip_idx, out_path.name,
            )
            continue

        logger.info(
            "[%d/%d] generate beat=%03d idx=%02d dur=%.2fs",
            idx, len(prompts), beat_id, clip_idx, duration,
        )
        for attempt in range(1, config.MAX_RETRIES + 1):
            try:
                provider.generate(prompt_entry["prompt"], duration, out_path)
                actual = probe_duration(out_path)
                entry = {
                    "beat_id": beat_id,
                    "clip_index": clip_idx,
                    "duration_target_sec": duration,
                    "duration_actual_sec": actual,
                    "filename": out_path.name,
                    "status": "success",
                }
                manifest_index[(beat_id, clip_idx)] = entry
                manifest["clips"] = list(manifest_index.values())
                _save_manifest(manifest_path, manifest)
                break
            except Exception:
                logger.warning("attempt %d/%d failed", attempt, config.MAX_RETRIES, exc_info=True)
                if attempt < config.MAX_RETRIES:
                    time.sleep(config.RETRY_DELAY)
                else:
                    entry = {
                        "beat_id": beat_id,
                        "clip_index": clip_idx,
                        "duration_target_sec": duration,
                        "filename": out_path.name,
                        "status": "failed",
                    }
                    manifest_index[(beat_id, clip_idx)] = entry
                    manifest["clips"] = list(manifest_index.values())
                    _save_manifest(manifest_path, manifest)

    logger.info("Manifest written to %s", manifest_path.name)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
