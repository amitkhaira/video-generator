"""Video provider factory and registry.

Pluggable video generation backends. Each provider advertises its
MAX_CLIP_SEC so the timeline planner (03_audio_timeline.py) can decide
whether beats must be split into scene-continuation chains.
"""

from __future__ import annotations

from .base import VideoProvider

_REGISTRY: dict[str, str] = {
    "meta_ai": "meta_ai_provider:MetaAIVideoProvider",
    "kling": "kling_provider:KlingProvider",
    "sora": "sora_provider:SoraProvider",
    "veo": "veo_provider:VeoProvider",
    "runway": "runway_provider:RunwayProvider",
    "wan": "wan_provider:WanProvider",
}


def get_provider(name: str) -> VideoProvider:
    key = (name or "").strip().lower()
    if key not in _REGISTRY:
        raise ValueError(
            f"Unknown VIDEO_PROVIDER '{name}'. Allowed: {sorted(_REGISTRY)}"
        )

    module_part, class_part = _REGISTRY[key].split(":")
    import importlib

    module = importlib.import_module(f".{module_part}", package=__name__)
    cls = getattr(module, class_part)
    return cls()


def provider_max_clip_sec(name: str) -> int:
    """Peek at a provider's MAX_CLIP_SEC without instantiating heavy clients."""
    key = (name or "").strip().lower()
    if key not in _REGISTRY:
        raise ValueError(f"Unknown video provider '{name}'")

    module_part, class_part = _REGISTRY[key].split(":")
    import importlib

    module = importlib.import_module(f".{module_part}", package=__name__)
    cls = getattr(module, class_part)
    return int(cls.MAX_CLIP_SEC)


__all__ = ["VideoProvider", "get_provider", "provider_max_clip_sec"]
