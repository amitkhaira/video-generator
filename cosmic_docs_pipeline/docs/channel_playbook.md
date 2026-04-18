# Channel Playbook — Cosmic Docs (Working Title)

The identity, niche, and production spec for the new Quera-style Hindi documentary channel. This file is the **single source of truth** for anything brand-related. The launch kit, thumbnail skill, and description templates all defer to what's defined here.

---

## 1. Channel Name — 5 Candidates

All five are evaluated on: Hindi resonance, memorability, domain availability (at time of writing), and SEO potential.


| #   | Name                 | Meaning / vibe                                   | Strengths                                                           | Risks                                           |
| --- | -------------------- | ------------------------------------------------ | ------------------------------------------------------------------- | ----------------------------------------------- |
| 1   | **Brahmand Files**   | "Universe Files" — evokes X-Files + cosmic scale | Strong Hindi ("Brahmand") + global tech ("Files") mashup, memorable | "Files" is used by many channels                |
| 2   | **Rahasya Lok**      | "World of Mysteries"                             | Pure Hindi, poetic, distinct                                        | Slightly niche, may sound traditional           |
| 3   | **The Ancient Code** | English name with mystery hook                   | Wider SEO reach, looks premium on banner                            | Loses Hindi-speaker affinity at first glance    |
| 4   | **Antariksh Docs**   | "Space Documentaries"                            | Clear niche signal, short                                           | "Antariksh" biases too science-only             |
| 5   | **Cosmic Kahani**    | "Cosmic Story"                                   | Story-first framing, warm, inclusive                                | May feel softer than Quera's authoritative tone |


### Recommendation

**Primary: `Brahmand Files`** — best mix of Hindi-first identity, memorability, and thematic range (fits mythology + science + philosophy without pigeonholing). This is the name referenced in the rest of the docs; change via a find-and-replace if you pick a different one.

**Backup: `Rahasya Lok`** if you want a fully Hindi brand.

---

## 2. Niche Definition

> **One-line pitch:** Cinematic Hindi documentaries at the intersection of cosmic mystery, spiritual science, and ancient wisdom — where Prometheus meets the Vedas.

### What we make

- 20-25 minute long-form Hindi cinematic documentaries (flagship)
- 60-90 second vertical Shorts (lead magnets) — one clip pulled from each long video + 1-2 standalone Shorts per week
- Community posts (occasional polls, topic teases)

### What we don't make

- News / current affairs
- Explainer videos under 10 minutes
- Dark-crime / true-crime content (that's `documentary_pipeline/` Vivek Docs territory)
- Live streams or reactions

### Audience

Primary: 18-40, Hindi-speaking, India + diaspora, interested in spirituality, science, philosophy, mythology, conspiracy-curious-but-thoughtful. Secondary: Urban English-comfortable viewers who prefer Hindi storytelling for this topic.

---

## 3. Brand Guidelines

### Color palette


| Role                       | Color     | Usage                                               |
| -------------------------- | --------- | --------------------------------------------------- |
| Primary — Deep Cosmic Blue | `#0A1535` | Backgrounds, shadows, thumbnail base                |
| Accent — Warm Gold         | `#E8A84D` | Text highlights, ancient artifact glows             |
| Contrast — Ivory White     | `#F2E9D8` | Subtitles, logo, clean text                         |
| Alert — Cosmic Red         | `#C03636` | Used sparingly — reveal moments, warning thumbnails |
| Depth — Obsidian           | `#050914` | Deep shadow / vignette edges                        |


All AI video clips get a **uniform color grade** during merge: push shadows toward cosmic blue, lift highlights toward warm gold, +12 % contrast, -8 % saturation. This is what gives the channel a recognizable visual signature.

### Typography

- Channel wordmark: `Cinzel` (serif with classical authority) or `Philosopher` (Hindi-compatible)
- Thumbnail text: `Bebas Neue` or `Impact` (condensed heavy sans for punch)
- Lower-thirds / subtitles: `Mukta` (Hindi-friendly sans)

### Music bed

- Orchestral + sitar / santoor fusion
- Low-volume throughout, swells timed to sentence endings (matches Quera's style)
- Royalty-free sources: Epidemic Sound "Cinematic India" playlists, YouTube Audio Library "Ambient Cinematic"

### Voice

- Male, informative + curious tone
- Default narrator: cloned via XTTS v2 from a 10-20 s sample in `voices/narrator.wav`
- Speech rate: 130 WPM Hindi

### Logo direction (to be produced separately)

- Abstract mandala-circuit hybrid (ancient geometry meets data lines)
- Single-color version first (gold on deep blue), animated intro card later

---

## 4. Video Format Spec

### Long-form (flagship)


| Attribute    | Spec                                                                          |
| ------------ | ----------------------------------------------------------------------------- |
| Duration     | 20-25 minutes (target 22 min)                                                 |
| Aspect ratio | 16:9                                                                          |
| Resolution   | 1080p minimum, 4K if provider supports                                        |
| Frame rate   | 24 fps (cinematic) or 30 fps                                                  |
| Audio        | Mono voiceover + stereo music bed (music at -18 LUFS, voice at -14 LUFS peak) |
| Chapters     | Mandatory — one per script section (auto-generated from beat timings)         |
| Subtitles    | Auto-generated via Whisper, manually verified                                 |


### Shorts


| Attribute    | Spec                                                                      |
| ------------ | ------------------------------------------------------------------------- |
| Duration     | 45-75 s                                                                   |
| Aspect ratio | 9:16                                                                      |
| Resolution   | 1080 × 1920                                                               |
| Source       | Best 60-second window from long video OR standalone cosmic-mystery teaser |
| Hook         | First 2 seconds must contain the shock frame                              |
| End card     | "Full kahani — channel par dekho"                                         |


---

## 5. Upload Cadence

Week one rhythm, scalable from there:


| Day     | Content                                            |
| ------- | -------------------------------------------------- |
| Mon     | (Rest / research)                                  |
| Tue     | Short #1 (standalone teaser)                       |
| Wed     | (Rest)                                             |
| Thu     | Community post (poll or teaser)                    |
| Fri     | Short #2 (cutdown from last Saturday's long video) |
| **Sat** | **Long video (flagship)** — 7-8 PM IST             |
| Sun     | (Rest)                                             |


**Why Saturday evening for long-form**: IST 7-8 PM = dinner + weekend wind-down, highest watch-time retention window per 2026 YouTube Studio data for Indian Hindi-speaking audiences.

---

## 6. Section Spine (applies to every long video)

Every flagship video follows this 7-section structure, baked into `skills/scriptwriter_skill.md`:

1. **HOOK** (0:00 – 0:55) — Shock question, zero intro
2. **POP-CULTURE ANCHOR** (0:55 – 3:30) — Hollywood film or recent book tied to the topic
3. **SCIENTIFIC LAYER** (3:30 – 8:00) — Real scientists, real papers, real phenomena
4. **MYTHOLOGY BRIDGE** (8:00 – 13:00) — Indian + global parallel myths / scriptures
5. **COSMIC SCALE** (13:00 – 18:00) — The "big numbers" beat — universe scale, Fermi, Kardashev, etc.
6. **PHILOSOPHICAL CLIMAX** (18:00 – 22:00) — Unify science and spirituality, famous quote
7. **OPEN ENDING + CTA** (22:00 – end) — No definitive answer, tasteful subscribe prompt, preview next video

Chapter markers in the final video map 1:1 to these sections.

---

## 7. Production Checklist (before uploading any video)

```
□ Hook lands in < 10 seconds — no "Hello guys" intro
□ Minimum 3 real scientists / experts cited in narration
□ Minimum 2 scripture / myth references (ideally Indian + Western parallel)
□ Description has 3-5 research paper links
□ 7 sections demarcated with chapters
□ Silence trim applied — no pause longer than 0.35 s anywhere
□ Color grade consistent across all clips
□ Thumbnail has ≤ 3 words, cosmic + ancient visual mashup
□ Outro closes with a famous science / philosophy quote
□ Next-video preview planted in pinned comment
```

---

## 8. What Makes This Channel Different from Vivek Docs


| Axis              | Vivek Docs                                    | Brahmand Files                            |
| ----------------- | --------------------------------------------- | ----------------------------------------- |
| Niche             | Dark Truth / crime / mystery                  | Cosmic mystery / spiritual science / myth |
| Length            | 5-6 min                                       | 20-25 min                                 |
| Tone              | Conversational Hinglish, friend telling story | Informative Hindi with English tech terms |
| Voice             | Casual, narrative                             | Authoritative, curious                    |
| Credibility layer | Low (local legend / rumor)                    | High (real scientists, papers)            |
| Visual palette    | Dark + green surveillance                     | Deep blue + warm gold cosmic              |
| Structure         | Linear mystery unveil                         | 7-section spine with philosophical climax |


Both channels can co-exist in your portfolio — they target different moods and audiences, with zero content overlap.