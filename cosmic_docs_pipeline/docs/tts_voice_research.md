# TTS Voice Research — Picking a Narrator for Cosmic Docs

Every TTS provider supported by this pipeline, ranked and compared for **Hindi cinematic documentary narration** in the Quera Official style.

---

## TL;DR — Recommendation Ladder

| Rank | Provider | When to use | Cost |
|---|---|---|---|
| **1 — Default** | **XTTS v2 (Coqui)** | You want voice cloning, total privacy, zero per-video cost | Free forever |
| 2 | ElevenLabs v3 | You want the absolute best naturalness and will pay | $5-22 / month |
| 3 | Gemini 3.1 Flash TTS — `Charon` | Free online, no Mac setup, quick drafts | Free (quota) |
| 4 | Piper | You want a fast CPU-only offline tool for rough drafts | Free forever |
| 5 | F5-TTS | You have a GPU and want maximum offline quality | Free (GPU recommended) |

**Why not Enceladus (your current choice)?** Enceladus is classified as "Breathy" by Google. Breathy works for ASMR and calm meditation but collapses on documentary. Quera's voice is **informative + curious + slightly authoritative** — breathy is the opposite of that.

---

## 1. XTTS v2 (Coqui) — DEFAULT

### Why we chose this as default

- **Voice cloning from 10-20 s** of clean audio — you can clone Quera's tone itself (record a clean sample in your own voice, or record a short Hindi narration from a voiceover artist and reuse for every video)
- **Offline, 100 % private** — no API cost ever
- **Hindi supported** natively (lang code `hi`)
- **Runs on Mac M-series** with MPS acceleration, or CPU fallback
- Apache / MPL license — safe for commercial use
- Consistency: same reference wav → same voice every single time, no drift

### Setup (one-time)

```bash
cd cosmic_docs_pipeline
pip install TTS>=0.22.0
```

On Apple Silicon, if the build fails on `deep-phonemizer`, drop back to Python 3.10 or 3.11 and retry with `pip install TTS --no-build-isolation`.

First call downloads ~2.3 GB of model weights to `~/.local/share/tts/` — this is a one-time cost.

### Voice cloning workflow

1. Record (or find) a 10-20 second clean Hindi narration sample.
   - Must be: clean microphone, minimal reverb, no background music, 16 kHz+, single speaker
   - Tip: record yourself reading one Quera-style paragraph, or extract from any creative commons Hindi documentary
2. Save as `cosmic_docs_pipeline/voices/narrator.wav`
3. Set in `.env`: `TTS_PROVIDER=xtts` and `TTS_REFERENCE_WAV=voices/narrator.wav`
4. Run `02_tts_generator.py` — first call warms the model (~30 s), subsequent calls are fast

### Expected performance on Mac M1/M2/M3

- Warmup: ~30 s
- Per sentence: ~1-3 s real-time on MPS, 3-8 s on CPU
- 22-min documentary (~250 sentences): 5-15 min total TTS time

### Quality characteristics

- Natural prosody, good intonation on Hindi
- Occasionally hiccups on long English-heavy technical loanwords (e.g. *"microscopic"*) — but recoverable on retry
- Not as dramatic as ElevenLabs, but consistent

---

## 2. ElevenLabs v3 — Premium online

### Why it's rank 2

- #1 on 2026 naturalness blind tests for Hindi
- Professional voice cloning from 30 s sample (instant voice cloning + professional voice cloning tiers)
- Consistent across videos once you pick or clone a voice
- API is rock solid

### Setup

```bash
pip install elevenlabs>=1.0.0
```

`.env`:
```
TTS_PROVIDER=elevenlabs
ELEVENLABS_API_KEY=sk_...
ELEVENLABS_MODEL=eleven_multilingual_v2
TTS_VOICE=<voice id from your ElevenLabs dashboard>
```

### Voice cloning (superior to XTTS)

Upload a 30 s-3 min clean sample to the ElevenLabs dashboard → get a voice ID → paste it in `TTS_VOICE`.

### Cost

- Free tier: 10 k chars/month (~10 min of audio — not enough for one full video)
- Starter $5/mo: 30 k chars
- Creator $22/mo: 100 k chars (enough for 4-5 full 22-min videos)

**Verdict**: Worth it when you cross the break-even line (>$22 of your time saved per month). Use XTTS for drafts, switch to ElevenLabs for final production.

---

## 3. Gemini 3.1 Flash TTS — Free online

### Why it's rank 3

- Free (quota limited but generous)
- 30+ voices with clear style labels — pick the right one, not Enceladus
- Built-in "audiobook narrator" style template
- Very good for drafts when you don't have time to run XTTS locally

### Voice picks for documentary

| Voice | Google label | Use |
|---|---|---|
| **`Charon`** | Informative | **Primary pick** — closest match to Quera tone |
| `Rasalgethi` | Informative | Warmer alternative |
| `Gacrux` | Mature | Gravitas-heavy climax sections |
| `Alnilam` | Firm | Authoritative reveals |
| `Sadaltager` | Knowledgeable | Science-heavy segments |
| `Iapetus` | Clear | Crisp factual beats |

Voices we **avoid** for this channel: `Enceladus` (breathy), `Aoede` (breezy), `Leda` (youthful), `Achernar` (soft).

### Setup (no install — uses existing `google-genai` from core deps)

`.env`:
```
TTS_PROVIDER=gemini
TTS_VOICE=Charon
GEMINI_API_KEY=<your key>
```

### Known weakness

Gender bias (better on male voices than female). If the channel narrator is male, this is actually fine for us.

---

## 4. Piper — Fastest offline option

### Why it's rank 4

- Fastest CPU-only neural TTS (real-time on modest hardware)
- Tiny model footprint (~50-100 MB per voice)
- Works well for rapid iteration when testing scripts

### Setup

```bash
pip install piper-tts>=1.2.0
# Download a Hindi voice model:
python -m piper --download-dir ~/.local/share/piper hi_IN-priyamvada-medium
```

`.env`:
```
TTS_PROVIDER=piper
TTS_VOICE=hi_IN-priyamvada-medium
```

### Limitations

- No voice cloning — stuck with the pre-trained Hindi voices
- Prosody is noticeably more robotic than XTTS or ElevenLabs
- Best used for: quick draft listening passes, smoke tests, CI

---

## 5. F5-TTS — Highest-quality offline (GPU)

### Why rank 5 for our use

- MIT license, Diffusion Transformer, excellent naturalness
- Voice cloning from short samples
- **GPU-recommended** — CPU is painfully slow (20-60 s per sentence)

On your Mac M-series, GPU acceleration for F5-TTS via MPS is still experimental as of April 2026. We leave the provider wired up for when you upgrade to a CUDA box or when MPS support matures.

### Setup (when ready)

```bash
pip install f5-tts
```

`.env`:
```
TTS_PROVIDER=f5
TTS_REFERENCE_WAV=voices/narrator.wav
```

---

## 6. Silence Trimming — The Quera "Flow" Trick

No matter which TTS you pick, the biggest single upgrade is **aggressive silence trimming**. Quera's narration feels tight because dead air is stripped out.

Our `utils/silence_trim.py` applies this ffmpeg filter to every generated beat:

```
silenceremove=stop_periods=-1:stop_duration=0.35:stop_threshold=-38dB
```

### Tuning table

| Goal | `stop_duration` | `stop_threshold` |
|---|---|---|
| **Default — Quera feel** | `0.35` | `-38dB` |
| Preserve more drama | `0.6` | `-42dB` |
| Ultra-tight (rap/breathless) | `0.2` | `-35dB` |
| Noisy source audio | `0.35` | `-30dB` (higher threshold tolerates room noise) |

Change these via `SILENCE_TRIM_DURATION` and `SILENCE_TRIM_THRESHOLD_DB` in `.env`.

---

## 7. Per-Emotion Voice Pick (when using Gemini)

Quera uses the same voice throughout but we can get more mileage by tagging beats in the script (this is a Phase-2 idea). For reference:

| Section | Mood | Gemini voice pick |
|---|---|---|
| HOOK | Curious, urgent | `Charon` |
| POP-CULTURE ANCHOR | Informative | `Charon` |
| SCIENTIFIC LAYER | Factual, composed | `Iapetus` or `Sadaltager` |
| MYTHOLOGY BRIDGE | Mystical, warm | `Rasalgethi` |
| COSMIC SCALE | Awe-inspired | `Gacrux` |
| PHILOSOPHICAL CLIMAX | Reflective, mature | `Gacrux` |

For v1 we stick with one voice per video — either XTTS cloned or Gemini `Charon`.

---

## 8. Diagnostic Script

To quickly compare voices side-by-side before committing, generate the same Hindi test sentence across all installed providers:

```bash
cd cosmic_docs_pipeline
# With XTTS (default)
TTS_PROVIDER=xtts python 02_tts_generator.py --diagnose "Yeh brahmand hamari kalpana se kahin zyada vishal hai."

# With Piper
TTS_PROVIDER=piper TTS_VOICE=hi_IN-priyamvada-medium python 02_tts_generator.py --diagnose "Yeh brahmand hamari kalpana se kahin zyada vishal hai."

# With Gemini
TTS_PROVIDER=gemini TTS_VOICE=Charon python 02_tts_generator.py --diagnose "Yeh brahmand hamari kalpana se kahin zyada vishal hai."
```

Listen to the resulting WAVs in `output/_diagnose/` and pick your favorite.

---

## 9. Whisper Helper (bonus, offline)

For subtitles or for reverse-engineering Quera's exact timing, use `utils/align_with_whisper.py`:

```bash
pip install faster-whisper
python utils/align_with_whisper.py path/to/audio.wav > word_timings.json
```

This runs entirely offline and produces word-level timestamps — useful for generating `.srt` subtitles from your final `voiceover.wav`.
