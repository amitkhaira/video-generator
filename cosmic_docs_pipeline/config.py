"""Shared configuration for the cosmic_docs_pipeline.

Audio-first, pluggable-provider architecture. All env keys read from the
pipeline-local .env (preferred) then falling back to the project root .env.
"""

from __future__ import annotations

import os
import re
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent

# Load .env from pipeline dir first (so pipeline-specific overrides win),
# then fall back to project root.
load_dotenv(BASE_DIR / ".env")
load_dotenv(BASE_DIR.parent / ".env")


# ── Topic → output subfolder ─────────────────────────────────────────
_QUOTE_CHARS = frozenset("\"'\"\u201c\u201d\u2018\u2019")
_TOPIC_SAFE_RE = re.compile(r"[^\w\s\-.,()'&\u0900-\u097F]+", re.UNICODE)


def normalize_story_text(text: str) -> str:
    """Strip surrounding ASCII / smart quotes from story / topic text."""
    s = text.strip()
    for _ in range(4):
        if not s:
            break
        if s[0] in _QUOTE_CHARS:
            s = s[1:].lstrip()
        if not s:
            break
        if s[-1] in _QUOTE_CHARS:
            s = s[:-1].rstrip()
    return s


def topic_folder_name(max_length: int = 100) -> str:
    """Derive a safe output folder name from the first line of story.txt."""
    story_path = BASE_DIR / "story.txt"
    if not story_path.exists() or story_path.stat().st_size == 0:
        return "untitled"
    raw = normalize_story_text(story_path.read_text(encoding="utf-8"))
    line = raw.split("\n", 1)[0].strip() if raw else ""
    line = _TOPIC_SAFE_RE.sub(" ", line)
    for bad in '\\/:*?"<>|':
        line = line.replace(bad, " ")
    line = re.sub(r"\s+", " ", line).strip().rstrip(". ")
    if not line:
        return "untitled"
    if len(line) > max_length:
        line = line[:max_length].rstrip()
    return line or "untitled"


def output_dir_path() -> Path:
    return BASE_DIR / "output" / topic_folder_name()


def beats_dir_path() -> Path:
    return output_dir_path() / "beats"


def clips_dir_path() -> Path:
    return output_dir_path() / "clips"


OUTPUT_DIR = str(output_dir_path())
BEATS_DIR = str(beats_dir_path())
CLIPS_DIR = str(clips_dir_path())


# ── Channel target ──────────────────────────────────────────────────
TARGET_MINUTES = int(os.getenv("TARGET_MINUTES", "22"))
SPEECH_RATE_WPM = int(os.getenv("SPEECH_RATE_WPM", "130"))


# ── LLM (script + video-prompt generation) ──────────────────────────
LLM_PROVIDERS = [
    p.strip().lower()
    for p in os.getenv("LLM_PROVIDERS", "gemini,openai,claude").split(",")
    if p.strip()
]
LLM_SELECTED = os.getenv("LLM_SELECTED", "claude").strip().lower()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")

# Model IDs — override in .env when a newer version releases.
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-pro")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o")
CLAUDE_MODEL = os.getenv("CLAUDE_MODEL", "claude-opus-4-5-20250914")


# ── TTS ─────────────────────────────────────────────────────────────
# Default: XTTS v2 (offline, voice cloning, free)
TTS_PROVIDER = os.getenv("TTS_PROVIDER", "xtts").strip().lower()
TTS_VOICE = os.getenv("TTS_VOICE", "").strip()
TTS_REFERENCE_WAV = os.getenv("TTS_REFERENCE_WAV", "voices/narrator.wav").strip()
TTS_LANGUAGE = os.getenv("TTS_LANGUAGE", "hi").strip()

# ElevenLabs
ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY", "")
ELEVENLABS_MODEL = os.getenv("ELEVENLABS_MODEL", "eleven_multilingual_v2")

# Gemini TTS (uses GEMINI_API_KEY)
GEMINI_TTS_MODEL = os.getenv("GEMINI_TTS_MODEL", "gemini-2.5-flash-preview-tts")
GEMINI_TTS_DEFAULT_VOICE = os.getenv("GEMINI_TTS_DEFAULT_VOICE", "Charon")


# ── Audio post-processing (silence trimming) ────────────────────────
SILENCE_TRIM_DURATION = float(os.getenv("SILENCE_TRIM_DURATION", "0.35"))
SILENCE_TRIM_THRESHOLD_DB = int(os.getenv("SILENCE_TRIM_THRESHOLD_DB", "-38"))


# ── Video provider ──────────────────────────────────────────────────
VIDEO_PROVIDER = os.getenv("VIDEO_PROVIDER", "meta_ai").strip().lower()

# If blank, the pipeline auto-fills from the provider's MAX_CLIP_SEC.
_raw_max_clip = os.getenv("VIDEO_MAX_CLIP_SEC", "").strip()
VIDEO_MAX_CLIP_SEC: int | None = int(_raw_max_clip) if _raw_max_clip.isdigit() else None

# Provider-specific settings
KLING_API_KEY = os.getenv("KLING_API_KEY", "")
KLING_MODEL = os.getenv("KLING_MODEL", "kling-v2.6")

SORA_API_KEY = os.getenv("SORA_API_KEY", "")
VEO_MODEL = os.getenv("VEO_MODEL", "veo-3.1")
RUNWAY_API_KEY = os.getenv("RUNWAY_API_KEY", "")
RUNWAY_MODEL = os.getenv("RUNWAY_MODEL", "gen-4")
WAN_API_KEY = os.getenv("WAN_API_KEY", "")
WAN_API_BASE = os.getenv("WAN_API_BASE", "")

# Meta AI cookies
META_AI_COOKIES_REQUIRED = ["META_AI_DATR", "META_AI_ECTO_1_SESS"]
META_AI_COOKIES_OPTIONAL = [
    "META_AI_ABRA_SESS",
    "META_AI_RD_CHALLENGE",
    "META_AI_DPR",
    "META_AI_WD",
]
META_AI_VIDEO_POLL_ATTEMPTS = int(os.getenv("META_AI_VIDEO_POLL_ATTEMPTS", "30"))
META_AI_VIDEO_POLL_WAIT = int(os.getenv("META_AI_VIDEO_POLL_WAIT", "5"))


# ── Thumbnail provider ──────────────────────────────────────────────
THUMB_PROVIDER = os.getenv("THUMB_PROVIDER", "gemini_image").strip().lower()


# ── YouTube ─────────────────────────────────────────────────────────
YOUTUBE_CLIENT_SECRETS_JSON = os.getenv("YOUTUBE_CLIENT_SECRETS_JSON", "").strip()
YOUTUBE_CLIENT_SECRETS_FILE = os.getenv(
    "YOUTUBE_CLIENT_SECRETS_FILE", "client_secret.json"
)
YOUTUBE_PRIVACY = os.getenv("YOUTUBE_PRIVACY", "private")
YOUTUBE_OAUTH_BROWSER = os.getenv("YOUTUBE_OAUTH_BROWSER", "").strip()


# ── FFmpeg ──────────────────────────────────────────────────────────
FFMPEG_PATH = os.getenv("FFMPEG_PATH", "ffmpeg")
FFPROBE_PATH = os.getenv("FFPROBE_PATH", "ffprobe")


# ── Retry / rate-limit defaults ─────────────────────────────────────
RATE_LIMIT_SECONDS = 15
MAX_RETRIES = 3
RETRY_DELAY = 30
DOWNLOAD_ATTEMPTS_PER_URL = 3
MIN_CLIP_BYTES = 1024


def resolve_video_max_clip_sec() -> int:
    """Return explicit override if set, else peek at provider's MAX_CLIP_SEC."""
    if VIDEO_MAX_CLIP_SEC is not None:
        return VIDEO_MAX_CLIP_SEC
    # Lazy import to avoid heavy imports at config load.
    from video_providers import provider_max_clip_sec

    return provider_max_clip_sec(VIDEO_PROVIDER)
