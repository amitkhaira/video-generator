"""Optional offline helper: word-level timestamp alignment via faster-whisper.

Not a mandatory pipeline stage — use this when you want:
  - Subtitles (.srt) generated from your final voiceover.wav
  - Reverse-engineering timing from an existing reference documentary
  - Cross-checking XTTS duration estimates

Install the optional dep:
    pip install faster-whisper

CLI:
    python -m utils.align_with_whisper path/to/audio.wav [--model large-v3] [--language hi]
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def align(
    audio_path: str | Path,
    *,
    model_name: str = "large-v3",
    language: str = "hi",
    device: str = "auto",
) -> list[dict]:
    """Return a list of {start, end, text, words: [{start, end, word}]} segments."""
    try:
        from faster_whisper import WhisperModel
    except ImportError as exc:
        raise RuntimeError(
            "faster-whisper not installed. pip install faster-whisper"
        ) from exc

    audio_path = str(audio_path)
    model = WhisperModel(model_name, device=device, compute_type="auto")
    segments, info = model.transcribe(
        audio_path,
        language=language,
        word_timestamps=True,
        vad_filter=True,
    )

    out: list[dict] = []
    for seg in segments:
        words = [
            {"start": w.start, "end": w.end, "word": w.word.strip()}
            for w in (seg.words or [])
        ]
        out.append(
            {
                "start": seg.start,
                "end": seg.end,
                "text": seg.text.strip(),
                "words": words,
            }
        )
    return out


def _parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Whisper word-level alignment")
    parser.add_argument("audio", type=Path, help="input audio file")
    parser.add_argument("--model", default="large-v3")
    parser.add_argument("--language", default="hi")
    parser.add_argument("--device", default="auto")
    parser.add_argument("--out", type=Path, default=None, help="output JSON path")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv if argv is not None else sys.argv[1:])
    segments = align(
        args.audio,
        model_name=args.model,
        language=args.language,
        device=args.device,
    )
    payload = {"segments": segments}
    if args.out:
        args.out.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"Wrote {args.out}")
    else:
        json.dump(payload, sys.stdout, ensure_ascii=False, indent=2)
        print()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
