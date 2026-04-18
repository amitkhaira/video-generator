---
name: cosmic-docs-thumbnail
description: Generate two thumbnail variant prompts (A/B) for a cosmic docs video, matching the channel's deep-blue + warm-gold brand palette and enforcing the ≤3-word text rule.
output_format: json
aspect_ratio: "16:9"
---

# Thumbnail Skill — Brahmand Files

Generate **two** AI-image prompts per video. We test A vs B on YouTube for the first 48 hours and keep the winner.

## Output Contract

```json
{
  "video_topic": "<topic from story.txt>",
  "variants": [
    {
      "label": "A",
      "style": "face-emotion",
      "prompt": "<full prompt>",
      "headline": "<≤3 words, UPPERCASE>",
      "overlay_spec": {"font": "Bebas Neue", "color": "#E8A84D", "stroke": "#050914"}
    },
    {
      "label": "B",
      "style": "mystery-element",
      "prompt": "<full prompt>",
      "headline": "<≤3 words, UPPERCASE>",
      "overlay_spec": {"font": "Impact", "color": "#F2E9D8", "stroke": "#0A1535"}
    }
  ]
}
```

## Composition Formula (mandatory)

Both variants must contain:

1. **One cosmic element** (galaxy / nebula / starfield / black hole / orbital ring)
2. **One ancient element** (temple silhouette / scripture / deity figure / artifact / ruin)
3. **Point of contact** — physical intersection of the cosmic + ancient element (e.g. nebula silhouetted through temple archway, glowing manuscript under aurora, ancient statue with glowing eyes reflecting stars)
4. **Negative space** on left OR right for the text overlay (don't clutter the whole frame)
5. **Deep cosmic blue + warm gold palette** — explicitly state this in the prompt
6. **High contrast, cinematic lighting, rim light on the subject**

## Style A — "Face Emotion" (curiosity-driven)

Formula:
```
Close to medium shot. A single human-face-like element (deity, rishi, astronaut helmet reflection, ancient statue) with visible emotion — awe, shock, or realization. The face is partially lit by [cosmic element]. Background has a secondary ancient element. High contrast, deep cosmic blue + warm gold color grade, cinematic lighting, 16:9.
```

**Example (Topic: Shiv = Alien?)**
```
Close-up of a stone statue of Lord Shiva with third-eye visibly glowing gold, one eye reflecting a swirling spiral galaxy, night sky visible around the statue, Mount Kailash silhouetted in background, warm gold rim light, deep cosmic blue shadows, hyperrealistic cinematic 16:9, empty space on right for text overlay, 4K, high contrast
```

Headline text: `SHIV = ALIEN?`
Font: Bebas Neue, gold (`#E8A84D`) with obsidian stroke (`#050914`), placed in right-side negative space, covering ~25-30% of frame width.

## Style B — "Mystery Element" (pattern-interrupt)

Formula:
```
Wide cinematic shot. Ancient element in foreground (ruin, artifact, scripture) with cosmic event behind it (galaxy spiraling, wormhole opening, orbital light). No human face. High intrigue, empty left or right third for text. Deep cosmic blue + warm gold palette, cinematic, 16:9.
```

**Example (Topic: Shiv = Alien?)**
```
Wide cinematic shot of Mount Kailash at night, apex of the mountain glowing gold from within as if housing something advanced, a subtle spiral galaxy swirling directly above the peak, ancient stone steps in foreground, deep cosmic blue shadows, warm gold highlights, dramatic clouds, empty space on left, hyperrealistic 16:9, 4K, cinematic lighting, high contrast
```

Headline text: `KAILASH SECRET`
Font: Impact, ivory (`#F2E9D8`) with deep cosmic blue stroke (`#0A1535`), placed in left third, covering ~28-32% of frame width.

## Headline Rules (strict)

- **Max 3 words**, UPPERCASE only
- Must tease the mystery, not spoil it
- One word ≤ 9 chars average for readability at 120×68 px mobile preview
- Avoid punctuation except `?`
- Never use emojis
- Word pairs from `docs/launch_kit.md` Section 5 are approved defaults

## Color + Font Rules (strict)

| Element | Spec |
|---|---|
| Primary text | `#E8A84D` (warm gold) OR `#F2E9D8` (ivory) |
| Text stroke | `#050914` or `#0A1535` (obsidian / cosmic blue) — 3-5 px |
| Drop shadow | optional, 0-2 px, very dark cosmic blue |
| Font family | Bebas Neue / Impact / Anton — condensed heavy sans only |
| Size | Text box = 25-35 % of frame width |
| Placement | Right third (A) or left third (B) — never center |

## Prompt Anti-Patterns (avoid)

- ❌ Text embedded inside the AI prompt itself ("with the word SHIV written") — AI image models render text unreliably. Always overlay text separately in post.
- ❌ Photorealistic faces of real people (living or recent historical figures) — stay abstract/statue/silhouette
- ❌ Copyrighted film characters or iconography
- ❌ Bright red / magenta — off-brand (use sparingly only on reveal-thumbnails via `#C03636` accent)
- ❌ Text longer than 3 words — kills thumbnail readability on mobile

## Process

1. Read `story.txt` to get the topic.
2. Check `docs/launch_kit.md` Section 5 for the approved headline for this topic (fall back to generating a new one if not listed).
3. Generate Variant A (face-emotion style) prompt.
4. Generate Variant B (mystery-element style) prompt.
5. Emit the JSON — the downstream `08_thumbnail_generator.py` sends each prompt to the configured image model (Gemini Image / Ideogram / DALL-E / Flux) and overlays the headline text in post.
