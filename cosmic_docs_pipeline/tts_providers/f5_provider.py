"""F5-TTS provider — high-quality offline TTS (GPU recommended).

Phase-2 wiring. Installation and API surface for F5-TTS is still evolving;
this stub exists so `TTS_PROVIDER=f5` produces a clear "not yet wired" error
rather than a mysterious ImportError.
"""

from __future__ import annotations

from pathlib import Path


class F5TTSProvider:
    id = "f5"

    def synthesize(
        self,
        text: str,
        out_path: str | Path,
        *,
        voice: str | None = None,
        reference_wav: str | Path | None = None,
        language: str = "hi",
    ) -> Path:
        raise NotImplementedError(
            "F5-TTS support is Phase-2. For offline voice cloning today, "
            "use TTS_PROVIDER=xtts (default) — it already supports voice "
            "cloning from a 10-20 s Hindi sample."
        )
