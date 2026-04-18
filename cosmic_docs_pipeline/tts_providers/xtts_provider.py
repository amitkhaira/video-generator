"""XTTS v2 (Coqui) TTS provider — DEFAULT offline voice-cloning TTS.

Voice cloning: provide a 10-20 s clean WAV of the target voice via
`reference_wav`. Hindi supported out of the box via `language="hi"`.

First call downloads ~2.3 GB of model weights to ~/.local/share/tts/.
"""

from __future__ import annotations

import logging
import threading
from pathlib import Path

logger = logging.getLogger("cosmic_docs.tts.xtts")

_MODEL_NAME = "tts_models/multilingual/multi-dataset/xtts_v2"
_model_lock = threading.Lock()
_cached_model = None


def _get_device() -> str:
    """Pick the best torch device for this machine (MPS → CUDA → CPU)."""
    try:
        import torch

        if torch.backends.mps.is_available():
            return "mps"
        if torch.cuda.is_available():
            return "cuda"
    except Exception:
        pass
    return "cpu"


class XTTSProvider:
    id = "xtts"

    def __init__(self) -> None:
        self._device = _get_device()
        logger.info("XTTS device resolved to: %s", self._device)

    def _load_model(self):
        global _cached_model
        with _model_lock:
            if _cached_model is not None:
                return _cached_model

            try:
                from TTS.api import TTS  # type: ignore
            except ImportError as exc:
                raise RuntimeError(
                    "Coqui TTS not installed. Install with: pip install TTS>=0.22.0"
                ) from exc

            logger.info("Loading XTTS v2 model (first call downloads ~2.3 GB)")
            model = TTS(_MODEL_NAME).to(self._device)
            _cached_model = model
            return model

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
            raise ValueError("XTTS: empty text")

        out = Path(out_path)
        out.parent.mkdir(parents=True, exist_ok=True)

        if not reference_wav:
            raise RuntimeError(
                "XTTS requires a reference WAV for voice cloning. "
                "Set TTS_REFERENCE_WAV or pass reference_wav= explicitly."
            )

        ref_path = Path(reference_wav)
        if not ref_path.is_absolute():
            # Resolve relative to the pipeline root (cosmic_docs_pipeline/)
            ref_path = Path(__file__).resolve().parent.parent / ref_path
        if not ref_path.exists():
            raise FileNotFoundError(
                f"XTTS reference WAV not found: {ref_path}. "
                f"Drop a 10-20 s clean Hindi sample there."
            )

        model = self._load_model()

        logger.info(
            "XTTS synthesize lang=%s ref=%s chars=%d → %s",
            language, ref_path.name, len(text), out.name,
        )
        model.tts_to_file(
            text=text,
            file_path=str(out),
            speaker_wav=str(ref_path),
            language=language,
        )
        return out
