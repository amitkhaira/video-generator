"""Abstract TTS provider contract."""

from __future__ import annotations

from pathlib import Path
from typing import Protocol, runtime_checkable


@runtime_checkable
class TTSProvider(Protocol):
    """Every concrete TTS provider implements this shape."""

    id: str

    def synthesize(
        self,
        text: str,
        out_path: str | Path,
        *,
        voice: str | None = None,
        reference_wav: str | Path | None = None,
        language: str = "hi",
    ) -> Path:
        """Synthesize `text` to a WAV file at `out_path`. Returns the Path."""
        ...
