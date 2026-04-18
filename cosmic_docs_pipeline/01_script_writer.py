#!/usr/bin/env python3
"""Stage 01 — Script Writer.

Reads story.txt + skills/scriptwriter_skill.md and asks the configured LLM
to produce a long-form Hindi cinematic documentary script as a beat-list
JSON. Optionally runs multiple LLMs in parallel and picks the selected one.

INPUT:
    story.txt                         — one-line topic
    skills/scriptwriter_skill.md      — style rules
    docs/quera_research.md            — few-shot reference (sentence patterns)

OUTPUT:
    output/<topic>/script.json                  — the winning variant
    output/<topic>/script.<provider>.json       — per-provider variants (for diffing)
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

logger = logging.getLogger("cosmic_docs.stage01")


def _setup_logging() -> None:
    logger.setLevel(logging.DEBUG)
    fmt = logging.Formatter("%(asctime)s  %(levelname)-7s  %(message)s", "%H:%M:%S")
    console = logging.StreamHandler(sys.stdout)
    console.setLevel(logging.INFO)
    console.setFormatter(fmt)
    logger.addHandler(console)


SYSTEM_INSTRUCTIONS = """You are the Brahmand Files cosmic documentary scriptwriter.
Follow scriptwriter_skill.md EXACTLY. Your output is ONE JSON object. No markdown. No prose.
If you cannot produce valid JSON, output NOTHING.
"""


def _read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _build_user_prompt(topic: str, skill: str, quera_excerpt: str) -> str:
    return f"""TOPIC (from story.txt):
{topic}

SCRIPTWRITER SKILL (follow exactly):

{skill}

REFERENCE — Quera Official sentence patterns (style, not content):

{quera_excerpt}

TASK:
Produce the FULL script as a single JSON object matching the output contract
in the skill. Target ~{config.TARGET_MINUTES} minutes at {config.SPEECH_RATE_WPM} WPM Hindi.
Include 180-280 beats across the 7 sections.

Return ONLY the JSON. No markdown fences, no commentary.
"""


_JSON_FENCE_RE = re.compile(r"```(?:json)?\s*(\{.*?\})\s*```", re.DOTALL)


def _extract_json(raw: str) -> dict:
    """Robustly extract the first top-level JSON object from the model output."""
    raw = raw.strip()
    m = _JSON_FENCE_RE.search(raw)
    if m:
        raw = m.group(1)
    # Trim to the first `{...}` balanced block if extra prose leaks in.
    if not raw.startswith("{"):
        start = raw.find("{")
        if start == -1:
            raise ValueError("No JSON object found in LLM output")
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


def _validate_script(payload: dict) -> None:
    if "beats" not in payload or not isinstance(payload["beats"], list):
        raise ValueError("Script missing `beats` list")
    if "sections" not in payload or not isinstance(payload["sections"], list):
        raise ValueError("Script missing `sections` list")
    for i, beat in enumerate(payload["beats"]):
        for key in ("id", "section_id", "text", "est_sec"):
            if key not in beat:
                raise ValueError(f"Beat #{i} missing field '{key}'")


def _call_provider(provider_name: str, system: str, user: str) -> dict | None:
    try:
        provider = get_provider(provider_name)
        logger.info("[%s] calling model …", provider_name)
        result = provider.generate(
            system=system,
            user=user,
            max_output_tokens=16384,
            temperature=0.9,
        )
        payload = _extract_json(result.text)
        _validate_script(payload)
        return payload
    except Exception:
        logger.warning("[%s] failed", provider_name, exc_info=True)
        return None


def _parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Stage 01 — Script Writer")
    parser.add_argument(
        "--providers", default=None,
        help="Comma-separated LLM providers (default: from config LLM_PROVIDERS)",
    )
    parser.add_argument(
        "--select", default=None,
        help="Which provider's output to copy to script.json (default: config LLM_SELECTED)",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    _setup_logging()
    args = _parse_args(argv if argv is not None else sys.argv[1:])

    providers = (
        [p.strip().lower() for p in args.providers.split(",") if p.strip()]
        if args.providers
        else config.LLM_PROVIDERS
    )
    selected = (args.select or config.LLM_SELECTED).lower()

    base_dir = Path(__file__).resolve().parent
    topic = _read_text(base_dir / "story.txt").strip()
    if not topic:
        logger.error("story.txt is empty — write a one-line topic first")
        return 2

    skill = _read_text(base_dir / "skills" / "scriptwriter_skill.md")
    quera = _read_text(base_dir / "docs" / "quera_research.md")
    # Keep the reference excerpt reasonable for token budget
    quera_excerpt = quera[:6000]

    user_prompt = _build_user_prompt(topic, skill, quera_excerpt)

    output_dir = Path(config.output_dir_path())
    output_dir.mkdir(parents=True, exist_ok=True)

    variants: dict[str, dict] = {}
    for prov in providers:
        payload = _call_provider(prov, SYSTEM_INSTRUCTIONS, user_prompt)
        if payload is None:
            continue
        variants[prov] = payload
        out_path = output_dir / f"script.{prov}.json"
        out_path.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        logger.info("[%s] wrote %s (%d beats)", prov, out_path.name, len(payload["beats"]))

    if not variants:
        logger.error("All LLM providers failed — no script produced")
        return 1

    winner = selected if selected in variants else next(iter(variants))
    final = output_dir / "script.json"
    final.write_text(
        json.dumps(variants[winner], ensure_ascii=False, indent=2), encoding="utf-8"
    )
    logger.info(
        "Selected '%s' as the winning variant → %s", winner, final.relative_to(base_dir)
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
