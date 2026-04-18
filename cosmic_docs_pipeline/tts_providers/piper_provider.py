"""Piper TTS provider — fastest CPU-only offline TTS (no cloning).

Download a Hindi voice model, e.g.:
    python -m piper --download-dir ~/.local/share/piper hi_IN-priyamvada-medium

Then set TTS_VOICE=hi_IN-priyamvada-medium in .env.
"""

from __future__ import annotations

import logging
import subprocess
from pathlib import Path

logger = logging.getLogger("cosmic_docs.tts.piper")

_DEFAULT_MODEL_DIR = Path.home() / ".local" / "share" / "piper"


class PiperProvider:
    id = "piper"

    def synthesize(
        self,
        text: str,
        out_path: str | Path,
        *,
        voice: str | None = None,
        reference_wav: str | Path | None = None,
        language: str = "hi",
    ) -> Path:
        if not text.strip():
            raise ValueError("Piper: empty text")
        if not voice:
            raise RuntimeError(
                "Piper requires TTS_VOICE (e.g. hi_IN-priyamvada-medium). "
                "Download via: python -m piper --download-dir ~/.local/share/piper <voice>"
            )

        out = Path(out_path)
        out.parent.mkdir(parents=True, exist_ok=True)

        # piper accepts a `.onnx` path or a model name; we resolve the common
        # ~/.local/share/piper/<voice>.onnx layout if the user gave a bare name.
        model_path = Path(voice)
        if not model_path.exists():
            candidate = _DEFAULT_MODEL_DIR / f"{voice}.onnx"
            if candidate.exists():
                model_path = candidate

        logger.info("Piper synthesize voice=%s → %s", voice, out.name)
        try:
            subprocess.run(
                [
                    "piper",
                    "--model", str(model_path),
                    "--output_file", str(out),
                ],
                input=text.encode("utf-8"),
                check=True,
                capture_output=True,
            )
        except FileNotFoundError as exc:
            raise RuntimeError(
                "piper CLI not found. Install with: pip install piper-tts"
            ) from exc
        except subprocess.CalledProcessError as exc:
            raise RuntimeError(
                f"Piper failed (exit {exc.returncode}): {exc.stderr.decode('utf-8', 'ignore')}"
            ) from exc

        return out
