"""
YouTube Shorts story templates — chunk-by-chunk format.

Each Short is keyed by a URL-friendly slug and contains:
  - title:          Human-readable title
  - description:    One-line summary (used in listings / logs)
  - total_duration: Approximate length in seconds
  - orientation:    VERTICAL (9:16) for Shorts
  - chunks:         Ordered list of ~8-second segment dicts
"""

from __future__ import annotations

SHORTS: dict[str, dict] = {
    # ------------------------------------------------------------------ #
    #  1. Sperm Whale Birth — First Drone Footage
    # ------------------------------------------------------------------ #
    "sperm-whale-birth": {
        "title": "Baby Sperm Whale Birth — First Drone Footage",
        "description": "First-ever drone footage of a sperm whale birth near Dominica",
        "total_duration": 64,
        "orientation": "VERTICAL",
        "chunks": [
            # ── Chunk 1 · Hook ───────────────────────────────────────
            {
                "chunk_number": 1,
                "time_range": "00:00-00:08",
                "section_type": "hook",
                "video_prompt": (
                    "Cinematic aerial drone shot over the deep Caribbean Sea "
                    "near Dominica, crystal blue water filling the entire frame. "
                    "A large dark shadow — barely visible — moves slowly beneath "
                    "the surface. Camera starts tight and pulls back slowly to "
                    "reveal the vast open ocean. Documentary style, golden hour "
                    "lighting, hyper-real colours, calm but ominous mood. "
                    "9:16 vertical frame."
                ),
                "voiceover": (
                    "Baby sperm whales are born underwater. "
                    "And they immediately start to sink."
                ),
                "onscreen_text": [],
                "audio_mood": "silence_ambient_tone",
                "transition": (
                    "Camera continues pulling back — cut on movement "
                    "to wider aerial shot of the research boat below."
                ),
            },
            # ── Chunk 2 · Build-up ───────────────────────────────────
            {
                "chunk_number": 2,
                "time_range": "00:08-00:16",
                "section_type": "buildup",
                "video_prompt": (
                    "Aerial drone view gliding forward over the calm Caribbean "
                    "Sea. A small white research vessel sits below, tiny against "
                    "the endless blue. On the deck, three scientists in blue "
                    "vests cluster around a laptop showing a live drone feed. "
                    "One scientist points excitedly at the screen. Cinematic "
                    "documentary feel, warm afternoon light, shallow focus "
                    "pulling from ocean to the boat's deck. 9:16 vertical frame."
                ),
                "voiceover": (
                    "For the first time ever, scientists caught a full sperm "
                    "whale birth on drone camera — and what happened next "
                    "changed everything we thought we knew."
                ),
                "onscreen_text": [
                    {
                        "text": "Dominica, Caribbean Sea — July 8, 2023",
                        "position": "lower_third",
                        "style": "default",
                    },
                ],
                "audio_mood": "ocean_waves_underscore",
                "transition": (
                    "Cut from aerial to a close-up of the laptop screen "
                    "showing 11 whales on the drone feed."
                ),
            },
            # ── Chunk 3 · Core — Discovery ───────────────────────────
            {
                "chunk_number": 3,
                "time_range": "00:16-00:24",
                "section_type": "core",
                "video_prompt": (
                    "Overhead drone shot looking straight down at the ocean "
                    "surface. Eleven large sperm whales visible from above, "
                    "clustered unusually close together — their dark elongated "
                    "shapes barely moving. Then suddenly the water around them "
                    "blooms red. Fast zoom-in from above as the water turns "
                    "crimson. Scientists on the boat in the background react "
                    "with wide-eyed shock. Hyper-real nature documentary "
                    "aesthetic, 9:16 vertical frame."
                ),
                "voiceover": (
                    "It was July 2023. Project CETI scientists tracked 11 "
                    "whales bunched together near the surface. Then — blood "
                    "turned the water red."
                ),
                "onscreen_text": [
                    {
                        "text": "11 whales. 2 unrelated families.",
                        "position": "center_bottom",
                        "style": "bold_large",
                    },
                ],
                "audio_mood": "silence_percussion_hit",
                "transition": (
                    "Smash cut from red water to extreme close-up of a baby "
                    "whale tail emerging from below the surface."
                ),
            },
            # ── Chunk 4 · Core — The Birth ───────────────────────────
            {
                "chunk_number": 4,
                "time_range": "00:24-00:32",
                "section_type": "core",
                "video_prompt": (
                    "Slow-motion aerial drone, looking straight down. A 4-metre "
                    "newborn sperm whale calf emerges from the mother tail-first "
                    "— visible as a dark elongated shadow surfacing. The calf "
                    "breaks the water surface and immediately begins sinking "
                    "back down. Water churns around it. The mother and two "
                    "other adult females are right alongside. Shot is tight, "
                    "120fps slow-motion aesthetic, blue-teal water, documentary "
                    "realism. 9:16 vertical frame."
                ),
                "voiceover": (
                    "They were witnessing a birth. A baby whale — 4 metres "
                    "long — emerged tail-first. And it was sinking."
                ),
                "onscreen_text": [
                    {
                        "text": "▮",
                        "position": "label",
                        "style": "label_bg",
                        "note": "Subtle yellow box highlight around the calf",
                    },
                ],
                "audio_mood": "orchestral_tension",
                "transition": (
                    "Hold on the sinking calf for one beat — then cut fast "
                    "as the first adult whale surges upward beneath it."
                ),
            },
            # ── Chunk 5 · Core — Teamwork ────────────────────────────
            {
                "chunk_number": 5,
                "time_range": "00:32-00:40",
                "section_type": "core",
                "video_prompt": (
                    "Overhead drone shot: multiple adult female sperm whales "
                    "swim in a coordinated pattern beneath and around the tiny "
                    "newborn calf. One whale gently lifts the calf from below "
                    "until its blowhole breaks the surface — first breath "
                    "visible as a burst of mist. A second unrelated adult whale "
                    "immediately takes the next turn, nudging the calf up "
                    "again. Fluid, graceful motion, slow-motion, turquoise-"
                    "deep-blue water, wide-angle drone perspective. "
                    "9:16 vertical frame."
                ),
                "voiceover": (
                    "Every single whale — even ones with zero relation to the "
                    "mother — took turns lifting the baby to breathe."
                ),
                "onscreen_text": [
                    {
                        "text": "Non-family members helping",
                        "position": "label",
                        "style": "label_bg",
                    },
                ],
                "audio_mood": "orchestral_wonder",
                "transition": (
                    "Cut from aerial whale view to a split-screen: underwater "
                    "audio waveform on left, drone footage on right."
                ),
            },
            # ── Chunk 6 · Core — The Science ─────────────────────────
            {
                "chunk_number": 6,
                "time_range": "00:40-00:48",
                "section_type": "core",
                "video_prompt": (
                    "Stylised split-screen visual: left side shows an animated "
                    "underwater audio waveform (clicking coda sounds pulsing in "
                    "rhythm), right side shows the top-down drone footage of "
                    "whales cooperating. Glowing white animated lines connect "
                    "each whale to the others, like a network diagram overlaid "
                    "on the real footage. Clean, futuristic documentary "
                    "infographic style. Deep blue tones throughout. "
                    "9:16 vertical frame."
                ),
                "voiceover": (
                    "Two unrelated whale families came together — hours before "
                    "the birth. They communicated in clicking sounds. "
                    "They planned this."
                ),
                "onscreen_text": [
                    {
                        "text": "Family A",
                        "position": "top",
                        "style": "label_bg",
                    },
                    {
                        "text": "Family B",
                        "position": "top_right",
                        "style": "label_bg",
                    },
                    {
                        "text": "Sound coordination",
                        "position": "lower_third",
                        "style": "subtle",
                    },
                ],
                "audio_mood": "whale_clicks_orchestral",
                "transition": (
                    "Split-screen collapses back into a single full-frame "
                    "aerial shot, camera pulling up for a wide vista."
                ),
            },
            # ── Chunk 7 · Payoff ─────────────────────────────────────
            {
                "chunk_number": 7,
                "time_range": "00:48-00:56",
                "section_type": "payoff",
                "video_prompt": (
                    "Wide cinematic drone shot from high altitude: all 11 "
                    "whales swimming in slow formation together through open "
                    "ocean, tiny against the vast blue expanse. The calf is "
                    "visibly in the centre, protected on all sides. Camera "
                    "slowly zooms out to maximum altitude — ocean fills the "
                    "frame. Golden hour light casts long shadows across the "
                    "water. Epic, awe-inspiring, no text yet. "
                    "9:16 vertical frame, maximum cinematic drama."
                ),
                "voiceover": (
                    "Scientists say this kind of non-family cooperation was "
                    "thought to be only a human thing. This behaviour is "
                    "36 million years old."
                ),
                "onscreen_text": [
                    {
                        "text": "36,000,000 years of cooperation.",
                        "position": "center",
                        "style": "bold_large",
                    },
                ],
                "audio_mood": "orchestral_swell",
                "transition": (
                    "Music softens as camera descends slightly — "
                    "cut to mother and calf swimming alone."
                ),
            },
            # ── Chunk 8 · CTA ────────────────────────────────────────
            {
                "chunk_number": 8,
                "time_range": "00:56-01:04",
                "section_type": "cta",
                "video_prompt": (
                    "Close aerial shot following the mother sperm whale and "
                    "her newborn calf swimming side by side through calm "
                    "turquoise water, moving deeper into the open ocean. "
                    "Camera tracks alongside at medium height. The calf stays "
                    "close to the mother's flank. Water is clear enough to see "
                    "both full bodies. Warm late-afternoon light. Peaceful, "
                    "hopeful, tender. Fade to slight vignette at edges as the "
                    "shot holds on the pair swimming into the deep blue. "
                    "9:16 vertical frame."
                ),
                "voiceover": (
                    "Nature is more connected than we ever imagined. "
                    "Follow for more wild science you won't believe is real."
                ),
                "onscreen_text": [
                    {
                        "text": "Follow for more",
                        "position": "center_bottom",
                        "style": "default",
                    },
                ],
                "audio_mood": "piano_gentle_fade",
                "transition": "Final frame — hold on the pair until fade to black.",
            },
        ],
    },
}


# ── Helpers ────────────────────────────────────────────────────────────
def get_short(slug: str) -> dict | None:
    """Return a Short dict by slug, or None if not found."""
    return SHORTS.get(slug)


def list_shorts() -> list[tuple[str, str]]:
    """Return a list of (slug, title) pairs for all available Shorts."""
    return [(slug, s["title"]) for slug, s in SHORTS.items()]
