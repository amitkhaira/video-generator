#!/usr/bin/env python3
"""Stage 04 — Video Prompt Generator.

Reads timeline.json (which knows the selected video provider's MAX_CLIP_SEC)
and asks the configured LLM to generate cinematic prompts per beat using
skills/visuals_skill.md. Emits video_prompts.json.

When a beat `needs_split`, the LLM chains prompts with scene-continuation
keywords so the downstream clip concat looks seamless.
"""

from __future__ import annotations

import argparse
import json
import logging
import re
import sys
from pathlib import Path

import config
from llm_providers import get_provider

logger = logging.getLogger("cosmic_docs.stage04")


def _setup_logging() -> None:
    logger.setLevel(logging.DEBUG)
    fmt = logging.Formatter("%(asctime)s  %(levelname)-7s  %(message)s", "%H:%M:%S")
    console = logging.StreamHandler(sys.stdout)
    console.setLevel(logging.INFO)
    console.setFormatter(fmt)
    logger.addHandler(console)


SYSTEM_INSTRUCTIONS = """You are the Brahmand Files cinematic video prompt engineer.
Follow visuals_skill.md EXACTLY. Output ONE JSON object matching the contract.
No markdown. No prose. If you cannot produce valid JSON, output NOTHING.
"""


_JSON_FENCE_RE = re.compile(r"```(?:json)?\s*(\{.*?\})\s*```", re.DOTALL)


def _extract_json(raw: str) -> dict:
    raw = raw.strip()
    m = _JSON_FENCE_RE.search(raw)
    if m:
        raw = m.group(1)
    if not raw.startswith("{"):
        start = raw.find("{")
        if start == -1:
            raise ValueError("No JSON in output")
        raw = raw[start:]
    depth = 0
    for i, ch in enumerate(raw):
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                raw = raw[: i + 1]
                break
    return json.loads(raw)


def _build_prompt(timeline: dict, skill: str) -> str:
    return f"""VIDEO PROVIDER: {timeline['video_provider']}
MAX_CLIP_SEC: {timeline['video_max_clip_sec']}

VISUALS SKILL (follow exactly):

{skill}

TIMELINE (input — each beat tells you how many clips and each duration):

{json.dumps({'beats': timeline['beats']}, ensure_ascii=False, indent=2)}

TASK:
Emit ONE JSON object:
{{
  "video_provider": "{timeline['video_provider']}",
  "prompts": [ ... one entry per clip in order ... ]
}}

Each prompt entry must have: beat_id, clip_index (0-based within beat),
duration_sec, prompt (string), aspect_ratio ("16:9"), continuation_of (null
for clip_index=0, otherwise {{"beat_id": X, "clip_index": Y}}).

For clip_index > 0 you MUST use the scene-continuation template from the skill
(SAME subject, SAME environment, CAMERA CONTINUES, SEAMLESS CONTINUATION,
NO CUT, etc.).

Every prompt must end with the duration suffix like ", 4.2s".
Every prompt must include "cinematic 16:9" and the color-grade clause.
Return ONLY the JSON.
"""


def _validate(payload: dict, timeline: dict) -> None:
    if "prompts" not in payload or not isinstance(payload["prompts"], list):
        raise ValueError("Missing prompts list")
    expected_total = sum(b["clip_count"] for b in timeline["beats"])
    actual = len(payload["prompts"])
    if actual != expected_total:
        logger.warning(
            "Prompt count mismatch: expected %d, got %d — downstream will fallback for missing.",
            expected_total, actual,
        )


def _fallback_fill(timeline: dict, prompts: list[dict]) -> list[dict]:
    """If the LLM omitted any clips, fill them with a conservative template."""
    by_key = {(p["beat_id"], p["clip_index"]): p for p in prompts}
    out: list[dict] = []
    for beat in timeline["beats"]:
        for clip_idx in range(beat["clip_count"]):
            key = (beat["id"], clip_idx)
            if key in by_key:
                out.append(by_key[key])
                continue
            dur = beat["clip_durations"][clip_idx]
            if clip_idx == 0:
                prompt = (
                    "Cinematic establishing shot related to: "
                    f"'{beat['text']}'. Deep cosmic blue shadows + warm gold highlights, "
                    f"high contrast, filmic grain, slow push-in, cinematic 16:9, 4K, {dur}s"
                )
                continuation_of = None
            else:
                prompt = (
                    "SAME subject from previous shot, SAME environment, SAME lighting — "
                    "CAMERA CONTINUES slow push-in, SEAMLESS CONTINUATION OF PREVIOUS SHOT, "
                    "NO CUT, NO SCENE CHANGE, cinematic 16:9, deep cosmic blue + warm gold, "
                    f"filmic grain, {dur}s"
                )
                continuation_of = {"beat_id": beat["id"], "clip_index": clip_idx - 1}
            out.append({
                "beat_id": beat["id"],
                "clip_index": clip_idx,
                "duration_sec": dur,
                "prompt": prompt,
                "aspect_ratio": "16:9",
                "continuation_of": continuation_of,
            })
    return out


def _parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Stage 04 — Video Prompt Generator")
    parser.add_argument("--provider", default=None, help="LLM provider override")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    _setup_logging()
    args = _parse_args(argv if argv is not None else sys.argv[1:])

    base_dir = Path(__file__).resolve().parent
    output_dir = Path(config.output_dir_path())

    timeline_path = output_dir / "timeline.json"
    if not timeline_path.exists():
        logger.error("timeline.json missing — run 03 first (%s)", timeline_path)
        return 2

    timeline = json.loads(timeline_path.read_text(encoding="utf-8"))
    skill = (base_dir / "skills" / "visuals_skill.md").read_text(encoding="utf-8")

    prompt_user = _build_prompt(timeline, skill)

    provider_name = (args.provider or config.LLM_SELECTED).lower()
    try:
        provider = get_provider(provider_name)
        logger.info("[%s] generating video prompts …", provider_name)
        result = provider.generate(
            system=SYSTEM_INSTRUCTIONS,
            user=prompt_user,
            max_output_tokens=16384,
            temperature=0.7,
        )
        payload = _extract_json(result.text)
        _validate(payload, timeline)
        prompts = payload.get("prompts", [])
    except Exception:
        logger.exception("[%s] LLM prompt generation failed — using full fallback template", provider_name)
        prompts = []

    # Fill any missing clips with the conservative template.
    prompts = _fallback_fill(timeline, prompts)

    out_payload = {
        "video_provider": timeline["video_provider"],
        "prompts": prompts,
    }
    out_path = output_dir / "video_prompts.json"
    out_path.write_text(json.dumps(out_payload, ensure_ascii=False, indent=2), encoding="utf-8")
    logger.info("Wrote %s (%d prompts)", out_path.name, len(prompts))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
