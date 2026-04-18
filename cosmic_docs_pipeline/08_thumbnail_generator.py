#!/usr/bin/env python3
"""Stage 08 — Thumbnail Generator (optional).

Reads skills/thumbnail_skill.md + story.txt, asks the LLM for two thumbnail
prompts (A: face-emotion, B: mystery-element), then sends each prompt to
the configured image model (THUMB_PROVIDER).

Supports: gemini_image | ideogram | dalle | flux (stub)

OUTPUT:
    output/<topic>/thumbnail_a.png
    output/<topic>/thumbnail_b.png
    output/<topic>/thumbnail_prompts.json
"""

from __future__ import annotations

import argparse
import base64
import json
import logging
import os
import re
import sys
from pathlib import Path

import requests

import config
from llm_providers import get_provider as get_llm_provider

logger = logging.getLogger("cosmic_docs.stage08")


def _setup_logging() -> None:
    logger.setLevel(logging.DEBUG)
    fmt = logging.Formatter("%(asctime)s  %(levelname)-7s  %(message)s", "%H:%M:%S")
    console = logging.StreamHandler(sys.stdout)
    console.setLevel(logging.INFO)
    console.setFormatter(fmt)
    logger.addHandler(console)


SYSTEM_INSTRUCTIONS = """You are the Brahmand Files thumbnail prompt engineer.
Follow thumbnail_skill.md EXACTLY. Output ONE JSON object. No markdown. No prose.
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


def _generate_image_gemini(prompt: str, out_path: Path) -> None:
    from google import genai
    from google.genai import types

    client = genai.Client(api_key=config.GEMINI_API_KEY)
    response = client.models.generate_content(
        model="gemini-2.5-flash-image-preview",
        contents=prompt,
        config=types.GenerateContentConfig(response_modalities=["IMAGE"]),
    )
    for part in response.candidates[0].content.parts:
        inline = getattr(part, "inline_data", None)
        if inline and getattr(inline, "data", None):
            raw = inline.data
            data = raw if isinstance(raw, bytes) else base64.b64decode(raw)
            out_path.write_bytes(data)
            return
    raise RuntimeError("Gemini image returned no inline_data")


def _generate_image_ideogram(prompt: str, out_path: Path) -> None:
    api_key = os.getenv("IDEOGRAM_API_KEY", "")  # set in .env
    if not api_key:
        raise RuntimeError("IDEOGRAM_API_KEY is not set")
    resp = requests.post(
        "https://api.ideogram.ai/generate",
        headers={"Api-Key": api_key, "Content-Type": "application/json"},
        json={
            "image_request": {
                "prompt": prompt,
                "aspect_ratio": "ASPECT_16_9",
                "model": "V_3",
                "magic_prompt_option": "AUTO",
            }
        },
        timeout=60,
    )
    resp.raise_for_status()
    body = resp.json()
    url = (body.get("data") or [{}])[0].get("url")
    if not url:
        raise RuntimeError(f"Ideogram: no url in response: {body}")
    img = requests.get(url, timeout=60)
    img.raise_for_status()
    out_path.write_bytes(img.content)


def _generate_image_dalle(prompt: str, out_path: Path) -> None:
    from openai import OpenAI

    client = OpenAI(api_key=config.OPENAI_API_KEY)
    response = client.images.generate(
        model="dall-e-3",
        prompt=prompt,
        n=1,
        size="1792x1024",
        response_format="b64_json",
    )
    data = base64.b64decode(response.data[0].b64_json)
    out_path.write_bytes(data)


def _generate_image_flux(prompt: str, out_path: Path) -> None:
    raise NotImplementedError(
        "Flux.1 image generation is not wired. Use THUMB_PROVIDER=gemini_image "
        "(default) or ideogram or dalle."
    )


_IMAGE_GENERATORS = {
    "gemini_image": _generate_image_gemini,
    "ideogram": _generate_image_ideogram,
    "dalle": _generate_image_dalle,
    "flux": _generate_image_flux,
}


def _parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Stage 08 — Thumbnail Generator")
    parser.add_argument("--provider", default=None, help="override THUMB_PROVIDER")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    _setup_logging()
    args = _parse_args(argv if argv is not None else sys.argv[1:])

    base_dir = Path(__file__).resolve().parent
    output_dir = Path(config.output_dir_path())
    output_dir.mkdir(parents=True, exist_ok=True)

    topic = (base_dir / "story.txt").read_text(encoding="utf-8").strip()
    skill = (base_dir / "skills" / "thumbnail_skill.md").read_text(encoding="utf-8")

    llm = get_llm_provider(config.LLM_SELECTED)
    user_prompt = f"""TOPIC: {topic}

SKILL:

{skill}

TASK: Emit the JSON per the thumbnail_skill contract (two variants A + B).
Return ONLY the JSON."""

    logger.info("Asking %s to draft thumbnail prompts …", config.LLM_SELECTED)
    result = llm.generate(
        system=SYSTEM_INSTRUCTIONS, user=user_prompt,
        max_output_tokens=4096, temperature=0.8,
    )
    payload = _extract_json(result.text)
    prompts_path = output_dir / "thumbnail_prompts.json"
    prompts_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    provider_name = (args.provider or config.THUMB_PROVIDER).lower()
    if provider_name not in _IMAGE_GENERATORS:
        raise SystemExit(
            f"Unknown THUMB_PROVIDER '{provider_name}'. "
            f"Allowed: {sorted(_IMAGE_GENERATORS)}"
        )
    generator = _IMAGE_GENERATORS[provider_name]

    variants = payload.get("variants", [])
    for variant in variants:
        label = variant.get("label", "X").upper()
        prompt = variant.get("prompt", "")
        out = output_dir / f"thumbnail_{label.lower()}.png"
        logger.info("Generating thumbnail %s with %s …", label, provider_name)
        try:
            generator(prompt, out)
            logger.info("  → %s", out.name)
        except Exception:
            logger.exception("thumbnail %s failed", label)

    logger.info(
        "Thumbnails written to %s (headlines applied in a separate step — overlay text in post)",
        output_dir,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
