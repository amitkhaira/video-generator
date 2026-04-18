#!/usr/bin/env python3
"""Stage 02 — TTS Generator (provider-agnostic, audio-first).

For each beat in script.json:
  1. Synthesize with the configured TTS provider (XTTS default).
  2. Silence-trim the raw WAV.
  3. Save trimmed WAV to output/<topic>/beats/NNN.wav.

Finally concatenate all trimmed beats into output/<topic>/voiceover.wav.

Resume: already-trimmed beats (NNN.wav) are skipped on rerun.
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
from tts_providers import get_provider
from utils.silence_trim import trim_silence

logger = logging.getLogger("cosmic_docs.stage02")


def _setup_logging() -> None:
    logger.setLevel(logging.DEBUG)
    fmt = logging.Formatter("%(asctime)s  %(levelname)-7s  %(message)s", "%H:%M:%S")
    console = logging.StreamHandler(sys.stdout)
    console.setLevel(logging.INFO)
    console.setFormatter(fmt)
    logger.addHandler(console)


def _load_script(path: Path) -> dict:
    if not path.exists():
        raise FileNotFoundError(f"script.json missing — run 01_script_writer.py first ({path})")
    return json.loads(path.read_text(encoding="utf-8"))


def _concat_wavs(beat_files: list[Path], out_path: Path) -> None:
    """Concatenate all beat WAVs into a single voiceover.wav via ffmpeg concat demuxer."""
    with tempfile.NamedTemporaryFile("w", suffix=".txt", delete=False, encoding="utf-8") as fh:
        list_file = Path(fh.name)
        for bf in beat_files:
            fh.write(f"file '{bf.resolve()}'\n")

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
            # concat copy can fail when headers differ — fall back to re-encode
            cmd = [
                config.FFMPEG_PATH, "-y",
                "-f", "concat",
                "-safe", "0",
                "-i", str(list_file),
                "-ar", "24000",
                "-ac", "1",
                str(out_path),
            ]
            proc = subprocess.run(cmd, capture_output=True, text=True)
            if proc.returncode != 0:
                raise RuntimeError(
                    f"ffmpeg concat failed: {proc.stderr[:500]}"
                )
    finally:
        list_file.unlink(missing_ok=True)


def _parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Stage 02 — TTS Generator")
    parser.add_argument("--force", action="store_true", help="re-synthesize all beats")
    parser.add_argument(
        "--limit", type=int, default=None, help="process only the first N beats"
    )
    parser.add_argument(
        "--diagnose", default=None,
        help="synthesize a single test sentence to output/_diagnose/<provider>.wav",
    )
    return parser.parse_args(argv)


def _diagnose(text: str) -> int:
    base_dir = Path(__file__).resolve().parent
    out_dir = base_dir / "output" / "_diagnose"
    out_dir.mkdir(parents=True, exist_ok=True)

    provider = get_provider(config.TTS_PROVIDER)
    raw_path = out_dir / f"{config.TTS_PROVIDER}.raw.wav"
    trimmed_path = out_dir / f"{config.TTS_PROVIDER}.wav"

    provider.synthesize(
        text,
        raw_path,
        voice=config.TTS_VOICE or None,
        reference_wav=config.TTS_REFERENCE_WAV or None,
        language=config.TTS_LANGUAGE,
    )
    trim_silence(raw_path, trimmed_path)
    logger.info("Diagnose wrote %s", trimmed_path)
    return 0


def main(argv: list[str] | None = None) -> int:
    _setup_logging()
    args = _parse_args(argv if argv is not None else sys.argv[1:])

    if args.diagnose:
        return _diagnose(args.diagnose)

    base_dir = Path(__file__).resolve().parent
    output_dir = Path(config.output_dir_path())
    beats_dir = Path(config.beats_dir_path())
    beats_dir.mkdir(parents=True, exist_ok=True)

    script_path = output_dir / "script.json"
    script = _load_script(script_path)
    beats = script["beats"]
    if args.limit:
        beats = beats[: args.limit]

    logger.info(
        "TTS provider=%s voice=%s ref=%s beats=%d",
        config.TTS_PROVIDER,
        config.TTS_VOICE or "<auto>",
        config.TTS_REFERENCE_WAV or "<none>",
        len(beats),
    )

    provider = get_provider(config.TTS_PROVIDER)

    final_wavs: list[Path] = []
    for idx, beat in enumerate(beats, start=1):
        beat_id = beat.get("id", idx)
        trimmed_path = beats_dir / f"{beat_id:03d}.wav"
        raw_path = beats_dir / f"{beat_id:03d}.raw.wav"

        if trimmed_path.exists() and trimmed_path.stat().st_size > 1000 and not args.force:
            logger.info("[%03d/%d] skip (exists) %s", idx, len(beats), trimmed_path.name)
            final_wavs.append(trimmed_path)
            continue

        text = (beat.get("text") or "").strip()
        if not text:
            logger.warning("[%03d/%d] empty beat text — skipping", idx, len(beats))
            continue

        logger.info("[%03d/%d] synth chars=%d", idx, len(beats), len(text))
        try:
            provider.synthesize(
                text,
                raw_path,
                voice=config.TTS_VOICE or None,
                reference_wav=config.TTS_REFERENCE_WAV or None,
                language=config.TTS_LANGUAGE,
            )
            trim_silence(raw_path, trimmed_path)
        except Exception:
            logger.exception("[%03d/%d] failed", idx, len(beats))
            raise

        final_wavs.append(trimmed_path)
        try:
            raw_path.unlink(missing_ok=True)
        except OSError:
            pass

    # Merge all trimmed beats into a single voiceover.wav
    voiceover_path = output_dir / "voiceover.wav"
    _concat_wavs(final_wavs, voiceover_path)
    logger.info("Merged %d beats → %s", len(final_wavs), voiceover_path.name)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
