# Video Model Research — Picking a Video Generator for Cosmic Docs

Every video provider supported by this pipeline, with max-clip duration, pricing, and the trade-off that matters most: **whether the scene-continuation trick is still needed**.

---

## TL;DR — Recommendation Ladder

| Rank | Provider | When to use | Max clip | Cost |
|---|---|---|---|---|
| **1 — Default** | **Meta AI** | Start here, free, scene-continuation handles the 5 s cap | 5 s | Free |
| 2 | Kling 2.6 / 3.0 | You want 60-120 s clips — scene-continuation problem disappears | 60-120 s | ~$10-20 / mo |
| 3 | Sora 2 | Premium cinematic for marquee videos | 10 s | $20 / mo (via ChatGPT Plus) |
| 4 | Veo 3.1 | 4K native, best character consistency | 8 s | Via Gemini API pricing |
| 5 | Runway Gen-4.5 | Motion brushes, creative control | 8 s | Expensive |
| 6 | WAN 2.5 | Middle-tier cinematic with synced audio | 10 s | Via Higgsfield/Pixara |

Key insight: **once you upgrade from Meta AI to Kling, every "scene continues seamlessly" prompt in `skills/visuals_skill.md` becomes optional**. The pipeline's `04_video_prompt_generator.py` auto-detects this and stops splitting beats.

---

## 1. Meta AI — DEFAULT (free)

### Why we chose this as default

- Genuinely free (with cookie auth)
- Already integrated in your existing pipeline — proven working
- Decent cinematic output at 16:9 and 9:16
- Our scene-continuation prompt design is built specifically to make 5 s clips feel seamless

### Setup

In `.env`:
```
VIDEO_PROVIDER=meta_ai
META_AI_DATR=<from your browser cookies>
META_AI_ECTO_1_SESS=<from your browser cookies>
```

See `documentary_pipeline/02_video_generator.py` in the parent project for the cookie extraction guide — same approach applies.

### 5 s cap — handled by scene-continuation

When `VIDEO_PROVIDER=meta_ai`, any script beat whose audio exceeds 5 s gets split. Example:

Beat text: *"Aur tab inhone dekha ki aasman se ek chamakta hua object neeche aa raha hai..."* (9 s audio)

- **Clip 1** (5.0 s): `"Ancient Indian sage standing on mountain, looking up, bright glowing object descending from night sky, slow zoom in, cinematic, 16:9 4K"`
- **Clip 2** (4.0 s): `"SAME ancient Indian sage, SAME mountain, SAME night sky — camera continues slowly forward, glowing object now closer and brighter, seamless continuation of previous shot, NO CUT, cinematic, 16:9 4K"`

Key phrases the prompt generator injects on continuation clips: `"SAME subject"`, `"SAME composition"`, `"SAME lighting"`, `"camera continues slowly"`, `"NO CUT"`, `"seamless continuation"`.

---

## 2. Kling 2.6 / 3.0 — Scene continuation killer

### Why it's rank 2

This is the **biggest quality-of-life upgrade**. Kling can generate a single clip up to 120 seconds. Most Quera-style script beats are 3-15 s — so every beat becomes a single clip. No splitting, no continuation prompts, no risk of visual discontinuity.

Kling also leads 2026 character-consistency benchmarks, which matters when the same narrator-persona ("ancient Indian sage", "NASA scientist", etc.) appears across multiple beats.

### Pricing (2026)

- Standard: ~$10/mo (basic quota)
- Pro: ~$20/mo (more credits, priority queue)

### Setup

```
VIDEO_PROVIDER=kling
KLING_API_KEY=<your key>
KLING_MODEL=kling-v2.6
```

The pipeline will automatically set `VIDEO_MAX_CLIP_SEC=60` for Kling and stop emitting split/continuation beats.

### When to upgrade

After your first 3-5 videos if you want visibly cleaner production. Meta AI → Kling is the single upgrade that most visibly lifts the final video toward Quera's polish.

---

## 3. Sora 2 — Premium cinematic

### Why rank 3

Industry-leading cinematic quality. Native synchronized audio (voice, sound effects). Realistic physics.

### The catch for us

- Still a 10 s clip cap — scene-continuation needed for many beats
- Requires ChatGPT Plus ($20/mo)
- Not always the fastest API-access path

### Best use case

Generate 2-3 **hero clips** per video in Sora and fill the rest with Kling or Meta AI. The pipeline's provider system lets you override per-clip if you want (future v2 feature).

---

## 4. Veo 3.1 — 4K native

### Why rank 4

- Native 4K output (future-proof, looks amazing on large screens)
- Strong character consistency (Google's research edge)
- Uses existing `GEMINI_API_KEY`

### The catch

- 8 s clip cap → still need continuation logic for longer beats
- Costs add up fast at 4K

### Setup

```
VIDEO_PROVIDER=veo
VEO_MODEL=veo-3.1
GEMINI_API_KEY=<same key as script LLM>
```

---

## 5. Runway Gen-4.5 — Motion brushes

### Why rank 5

Best-in-class creative control — draw motion paths directly on the frame. Useful for specific "camera orbiting an artifact" shots that Kling can't quite nail.

### Why not higher

Expensive per-clip, no native audio, 8 s cap. Best kept as a specialty tool for 1-2 hero shots per video once you're comfortable with the pipeline.

---

## 6. WAN 2.5 — Middle tier

### Why rank 6

- 10 s clips, 4K, synchronized audio
- Multi-lingual prompt support (Chinese + English strongest)
- Available via Higgsfield, Pixara, ImagineArt

### Why not higher

Access is fragmented (multiple API aggregators, inconsistent pricing), and quality is roughly on par with Kling while Kling has longer clips and a dedicated API.

Kept in the roster for completeness — if one of the aggregators offers a better deal in your region, you can switch via `VIDEO_PROVIDER=wan`.

---

## Scene-Continuation Logic — How the pipeline decides

`03_audio_timeline.py` runs after TTS and checks each beat against the selected provider's `MAX_CLIP_SEC`:

```
if beat.audio_sec <= provider.MAX_CLIP_SEC:
    beat.clip_count = 1
else:
    beat.clip_count = ceil(beat.audio_sec / provider.MAX_CLIP_SEC)
    beat.clip_durations = [evenly-distributed slices]
```

`04_video_prompt_generator.py` then generates prompts accordingly:

- `clip_count == 1` → single cinematic prompt, full beat text in context
- `clip_count > 1` → first clip is establishing shot; subsequent clips explicitly lock to same subject/composition/lighting with continuation keywords

This means **switching providers is literally one env-var change** — no code, no skill rewrites. The visuals skill file contains both prompt shapes; the generator picks the right one.

---

## Cost Math (for a 22-min cosmic docs video)

Typical video: 250 beats, average audio duration 5.3 s.

| Provider | Clips needed | Est. cost per video | Est. monthly (4 videos) |
|---|---|---|---|
| Meta AI | ~300 (with splits) | $0 | $0 |
| Kling | ~180 (longer clips) | Included in $20/mo | $20 |
| Sora 2 | ~250 (with splits) | Included in ChatGPT+ | $20 |
| Veo 3.1 | ~280 (with splits) | ~$0.50-2 per video | ~$2-8 |
| Runway | ~280 | ~$5-10 per video | ~$20-40 |

**Starter recommendation**: run everything on Meta AI for your first 4-5 videos, upgrade to Kling once the channel pulls in ad revenue.

---

## Quality Sanity Check — Before Committing

Before you switch providers, generate the **same 3-clip test prompt set** on both the old and new provider and A/B them:

```bash
# Generate test clips on Meta AI (current)
VIDEO_PROVIDER=meta_ai python 05_video_generator.py --test-prompts

# Generate test clips on Kling
VIDEO_PROVIDER=kling python 05_video_generator.py --test-prompts
```

The `--test-prompts` flag (wired in stage 5) produces a 3-clip sample from `skills/visuals_skill.md`'s archetype library. Watch side-by-side before paying for a month of Kling.
