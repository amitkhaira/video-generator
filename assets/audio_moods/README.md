# Audio Mood Files

Place royalty-free audio files in this directory to add ambient sound and
music to each chunk of your YouTube Shorts.

## Naming convention

Each chunk in `shorts_stories.py` has an `audio_mood` tag (e.g.
`"orchestral_swell"`).  The pipeline looks for a file named
`<mood_tag>.<ext>` in this folder.

Supported extensions: `.mp3`, `.wav`, `.m4a`, `.ogg`

## Tags used by the sperm whale Short

| Tag                       | Description                                      |
|---------------------------|--------------------------------------------------|
| `silence_ambient_tone`    | Silence, then a single deep ambient tone builds  |
| `ocean_waves_underscore`  | Ambient ocean waves, low cinematic underscore     |
| `silence_percussion_hit`  | Music cuts to silence, then a low percussion hit  |
| `orchestral_tension`      | Single sustained orchestral note — tension        |
| `orchestral_wonder`       | Warm, rising orchestral score — wonder            |
| `whale_clicks_orchestral` | Sperm whale clicking codas + orchestral score     |
| `orchestral_swell`        | Full orchestral swell — peak emotional moment     |
| `piano_gentle_fade`       | Calm ambient, single piano note closing           |

## Example

```
assets/audio_moods/
  orchestral_swell.mp3
  ocean_waves_underscore.wav
  piano_gentle_fade.mp3
  ...
```

If a file is missing for a chunk's mood tag the pipeline still works —
only the voiceover audio will be included for that chunk.

## Volume

The mood track is mixed beneath the voiceover at ~15% volume by default.
Override with `--mood-volume 0.20` on the CLI.
