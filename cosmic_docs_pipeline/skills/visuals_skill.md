---
name: cosmic-docs-visuals
description: Generate cinematic AI-video prompts for each script beat, handling multi-clip scene-continuation when the selected video provider has a clip-length cap shorter than the beat's audio duration.
output_format: json
aspect_ratio_default: "16:9"
color_grade: "deep cosmic blue shadows, warm gold highlights, high contrast, slight desaturation, filmic"
---

# Visuals Skill — Brahmand Files

You generate cinematic AI-video prompts for each script beat. You receive `timeline.json` (produced by `03_audio_timeline.py`) as input and emit `video_prompts.json`.

## Input shape (from `03_audio_timeline.py`)

```json
{
  "video_provider": "meta_ai",
  "video_max_clip_sec": 5,
  "beats": [
    {"id": 1, "section_id": "hook", "text": "...", "audio_sec": 4.1, "needs_split": false, "clip_count": 1, "clip_durations": [4.1]},
    {"id": 2, "section_id": "hook", "text": "...", "audio_sec": 8.5, "needs_split": true, "clip_count": 2, "clip_durations": [5.0, 3.5]}
  ]
}
```

## Output shape (must match exactly)

```json
{
  "video_provider": "meta_ai",
  "prompts": [
    {
      "beat_id": 1,
      "clip_index": 0,
      "duration_sec": 4.1,
      "prompt": "<full cinematic prompt>",
      "aspect_ratio": "16:9",
      "continuation_of": null
    },
    {
      "beat_id": 2,
      "clip_index": 0,
      "duration_sec": 5.0,
      "prompt": "<establishing shot prompt>",
      "aspect_ratio": "16:9",
      "continuation_of": null
    },
    {
      "beat_id": 2,
      "clip_index": 1,
      "duration_sec": 3.5,
      "prompt": "<continuation prompt locking to previous clip>",
      "aspect_ratio": "16:9",
      "continuation_of": {"beat_id": 2, "clip_index": 0}
    }
  ]
}
```

## 7 Shot Archetypes (pick one per beat based on text content)

| Archetype | When to use | Prompt seed |
|---|---|---|
| **Cosmic Wide** | Beats about universe scale, stars, galaxies | `"Vast cosmic vista, swirling nebula, billions of stars, deep space, scale emphasized by tiny planet in foreground, cinematic 16:9, deep blue + gold color grade, 4K, slow zoom"` |
| **Ancient Ruin** | Beats about scriptures, old civilizations | `"Weathered sandstone temple, intricate carved reliefs glowing in warm gold sunset, mysterious symbols, cinematic wide shot, 16:9, slow dolly push, atmospheric dust particles"` |
| **Ethereal Figure** | Beats about deities, rishis, spiritual figures | `"Silhouette of meditating sage on mountaintop, long white beard, flowing robes, aura of golden light, deep blue night sky with visible galaxy, ultra-cinematic, slow reveal"` |
| **Scripture Close-up** | Beats citing specific texts, shlokas | `"Ancient Sanskrit manuscript, parchment texture, golden ink, glowing letters, candlelight, extreme close-up, shallow depth of field, cinematic 16:9"` |
| **Lab / Telescope** | Beats citing modern science, scientists, studies | `"Modern observatory interior, scientist silhouette against giant reflecting telescope, computer screens showing star data, cool blue lighting with warm monitor glow, cinematic"` |
| **Alien Engineer** | Beats about ancient-alien hypothesis | `"Tall humanoid figure in iridescent biomechanical suit, standing on ancient Earth landscape, glowing symbols on armor, hyperrealistic, cinematic wide, awe-inspiring scale"` |
| **Match-cut Transition** | Beats bridging science to mythology | `"Match cut from DNA helix spiral rotating to spiral of ancient mandala carved in stone, seamless morph, warm gold on deep blue, cinematic"` |

## Prompt Template (single-clip beats)

```
<ARCHETYPE SEED>, <beat-specific subject>, <beat-specific action>, <camera movement>, cinematic 16:9, deep cosmic blue shadows + warm gold highlights, high contrast, filmic grain, <duration_sec>s
```

Camera movement options (rotate, don't repeat consecutively):
- `slow push-in` / `slow pull-back`
- `slow orbit left` / `slow orbit right`
- `locked-off tripod` (for reveals)
- `handheld slight shake` (rare, high-tension beats)
- `crane rise` / `crane fall`
- `dolly-zoom vertigo effect` (climax beats only)

## Scene-Continuation Template (multi-clip beats)

For any beat where `needs_split: true` and `clip_count > 1`:

### Clip 0 (establishing shot)

Same shape as single-clip prompt, but add:
```
"this is the establishing shot of a <clip_count>-part continuous scene"
```

### Clips 1..N-1 (continuation clips)

Use this EXACT prompt skeleton (keywords in CAPS are critical for seamless continuity):

```
SAME <subject from clip 0>, SAME environment, SAME lighting, SAME color palette — CAMERA CONTINUES <direction>, <micro-action progressing>, SEAMLESS CONTINUATION OF PREVIOUS SHOT, NO CUT, NO SCENE CHANGE, same cinematic 16:9 framing, deep cosmic blue + warm gold, filmic grain, <duration_sec>s
```

### Micro-action examples (progressions within the continuation)

- `"object moving slowly closer"` / `"object moving slowly farther"`
- `"light growing brighter"` / `"light dimming"`
- `"particles/dust/snow starting to fall"`
- `"camera continues forward by another 2 meters"`
- `"character takes one slow step"`
- `"stars slowly swirling further"`

Never introduce a new character, a new object, or a new environment in a continuation clip. The only thing that changes is the micro-progression.

### Example — 2-clip beat

Beat text: *"Aur tab inhone dekha ki aasman se ek chamakta hua object neeche aa raha hai, jiski roshni itni tez thi ki poori raat din jaisi ho gayi."* (audio 8.5 s, split 5.0 + 3.5)

**Clip 0 (5.0 s, establishing):**
```
Ancient Indian sage with long white beard, standing on mountaintop at night, looking up at dark starry sky, a small bright glowing white-gold orb appearing high above and slowly descending, cinematic wide shot 16:9, slow push-in, deep cosmic blue shadows with warm gold orb glow, high contrast, filmic grain, this is the establishing shot of a 2-part continuous scene, 5s
```

**Clip 1 (3.5 s, continuation):**
```
SAME ancient Indian sage with long white beard, SAME mountaintop, SAME dark starry sky — CAMERA CONTINUES slow push-in, the glowing orb is now much closer and brighter, night sky beginning to turn gold-white around it, wind stirring the sage's hair, SEAMLESS CONTINUATION OF PREVIOUS SHOT, NO CUT, NO SCENE CHANGE, same cinematic 16:9 framing, deep cosmic blue + warm gold, filmic grain, 3.5s
```

## Pattern-Interrupt Rule (every ~30 s)

To keep viewer retention high, alternate between archetypes. Never use the same archetype for more than 2 consecutive beats. The generator MUST track the archetype sequence and enforce variation.

## Section-Specific Visual Direction

| Section | Dominant archetypes | Color lean |
|---|---|---|
| Hook | Cosmic Wide + dramatic reveal | Deep blue dominant |
| Pop-culture anchor | Film still / cinematic homage | Warm and dramatic |
| Scientific layer | Lab / Telescope + diagrams | Cool blue + monitor green |
| Mythology bridge | Ancient Ruin + Scripture Close-up + Ethereal Figure | Warm gold dominant |
| Cosmic scale | Cosmic Wide + vastness | Deep space blue-black |
| Climax | Ethereal Figure + Match-cut | Gold + blue balance |
| Outro | Cosmic Wide receding | Soft blue fade |

## Hard Constraints

- **Every prompt MUST end with the duration** (`Xs`) so providers that use it can parse timing.
- **Every prompt MUST include `cinematic 16:9`** (or `9:16` for Shorts derivatives).
- **Every prompt MUST include the color-grade clause:** `"deep cosmic blue shadows + warm gold highlights"` — this is what makes the channel visually recognizable.
- **Never reference real living people by name in prompts** (copyright-safe).
- **Never reference copyrighted film characters by name in prompts** (say "sci-fi alien engineer in biomechanical suit" not "Prometheus Engineer").

## Process

1. Read `timeline.json`.
2. For each beat:
   a. Pick 1 archetype based on the text content (follow section-specific direction).
   b. If `clip_count == 1`, emit one prompt using single-clip template.
   c. If `clip_count > 1`, emit clip 0 (establishing) + clips 1..N-1 (continuation), locking all to the same subject/environment/lighting.
3. Alternate archetypes to avoid consecutive repeats beyond the 2-beat rule.
4. Emit the JSON. No prose.
