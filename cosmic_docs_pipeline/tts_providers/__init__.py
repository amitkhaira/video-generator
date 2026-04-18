"""TTS provider factory and registry.

Pluggable TTS backends. The default is XTTS v2 (offline, voice cloning).
Swap via TTS_PROVIDER env var.
"""

from __future__ import annotations

from .base import TTSProvider

_REGISTRY: dict[str, str] = {
    "xtts": "xtts_provider:XTTSProvider",
    "piper": "piper_provider:PiperProvider",
    "gemini": "gemini_provider:GeminiTTSProvider",
    "elevenlabs": "elevenlabs_provider:ElevenLabsProvider",
    "f5": "f5_provider:F5TTSProvider",
}


def get_provider(name: str) -> TTSProvider:
    """Factory: resolve provider name → instantiated TTSProvider.

    Lazy imports so a missing optional dependency (e.g. TTS lib for XTTS)
    only fails when that specific provider is selected.
    """
    key = (name or "").strip().lower()
    if key not in _REGISTRY:
        raise ValueError(
            f"Unknown TTS_PROVIDER '{name}'. Allowed: {sorted(_REGISTRY)}"
        )

    module_part, class_part = _REGISTRY[key].split(":")
    import importlib

    module = importlib.import_module(f".{module_part}", package=__name__)
    cls = getattr(module, class_part)
    return cls()


__all__ = ["TTSProvider", "get_provider"]
