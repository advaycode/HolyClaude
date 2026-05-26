# Audio Pipeline

Seedance 1.5 Pro / 2.0 generate audio and video jointly. We can't joint-train on a 4070. We approximate with **MMAudio** for ambient/Foley/music and **LatentSync** for lip-sync.

---

## Pipeline

```
video.mp4  ──┐
             ├──► MMAudio (V2A)  ──► video_with_ambient.mp4
text prompt ─┘                       (synced foley + music + ambient)

              if dialogue:
                                     │
                                     ▼
                            ┌────────────────┐
                            │  TTS (Piper /  │
                            │  ElevenLabs)   │
                            └────────┬───────┘
                                     │  speech.wav
                                     ▼
                            ┌────────────────┐
                            │   LatentSync   │ ◄── video_with_ambient.mp4
                            └────────┬───────┘
                                     │
                                     ▼
                            final_lipsynced.mp4
```

---

## MMAudio (video → ambient audio)

### Install (handled by install script)
```powershell
pip install mmaudio
```
Weights download on first use (~3 GB).

### CLI usage

```powershell
python scripts/add_audio.py \
  --video out/clip.mp4 \
  --prompt "soft wind through trees, distant temple bell, ambient pads" \
  --duration 5 \
  --out out/clip_with_audio.mp4
```

### What MMAudio is good at
- **Foley**: footsteps, doors, fabric rustle, water
- **Ambient**: room tone, wind, rain, traffic
- **Music**: short pads, motifs, drones (limited; not a full music model)
- **Onomatopoeic action**: a punch, a shot, a thunk

### What MMAudio is NOT good at
- **Speech / dialogue** — use TTS + lip-sync instead
- **Long musical scores** — use Suno API or Stable Audio Open for music tracks
- **Complex multi-source audio** — generates a single mixed track

### Tuning

| Flag | Effect |
|---|---|
| `--prompt "..."` | Text guidance for the audio character |
| `--duration N` | Audio length in seconds (must match video) |
| `--num-steps 25` | Diffusion steps; default 25, drop to 15 for faster |
| `--cfg 4.5` | CFG for text-audio guidance |
| `--seed N` | Reproducibility |
| `--sync-mode strict` | Tighter audio-video frame alignment (slower) |

VRAM: ~5 GB. Wall time: ~30 s for 5 s of audio on 4070.

---

## LatentSync (lip-sync)

For talking heads. Takes a video with a face + an audio of speech → re-renders the mouth region to match the audio.

### Usage

```powershell
# Step 1: get speech audio (either bring your own or generate)
python scripts/tts.py --text "Welcome to the future of video." --voice piper-en-amy --out out/speech.wav

# Step 2: lip-sync the video to the speech
python scripts/lipsync.py --video out/portrait.mp4 --audio out/speech.wav --out out/talking.mp4
```

Or end-to-end:

```powershell
python scripts/add_audio.py \
  --video out/portrait.mp4 \
  --tts "Welcome to the future of video." \
  --voice piper-en-amy \
  --lipsync \
  --out out/talking_head.mp4
```

### Notes
- LatentSync expects a clear, frontal-ish face. Side profiles fail.
- Best at 25 fps. If your video is at 24 or 30, the script handles resampling.
- VRAM: ~6 GB.
- Wall time: ~1 min per second of video.

---

## TTS options

| Option | Speed | Quality | Cost |
|---|---|---|---|
| **Piper TTS (local)** | very fast | decent | free |
| **ElevenLabs API** | fast | excellent | $5/mo+ |
| **Cartesia API** | fast | excellent | usage-based |
| **F5-TTS (local, voice cloning)** | medium | great | free, ~6 GB |
| **CosyVoice 2 (local)** | medium | great, multilingual | free, ~7 GB |

`scripts/tts.py` supports all five; default is Piper for offline-only.

---

## Music

MMAudio handles short ambient/pad music. For full music tracks:

### Option 1 — Stable Audio Open (local)
- 45 s max, 44.1 kHz, fits in 8 GB VRAM
- `scripts/music.py --backend stable-audio-open --prompt "..."`

### Option 2 — Suno API
- Up to 4 min, vocals + instrumentals
- Paid, ~$10/mo for casual use
- `scripts/music.py --backend suno --prompt "..."`

### Option 3 — MusicGen Large (local)
- 30 s segments, instrumental, 16 kHz
- ~6 GB VRAM
- `scripts/music.py --backend musicgen --prompt "..."`

---

## Full audio composition

For a hero shot with ambient + music + dialogue:

```powershell
python scripts/compose_audio.py \
  --video out/hero.mp4 \
  --ambient "rain on pavement, distant city" \
  --music "cinematic orchestral build, low strings, gentle piano" \
  --music-backend stable-audio-open \
  --dialogue "And then it began." \
  --voice elevenlabs-rachel \
  --lipsync \
  --out out/hero_final.mp4
```

What it does:
1. Generates ambient with MMAudio (5 s, -12 dB)
2. Generates music with chosen backend (5 s, -6 dB)
3. Generates dialogue TTS, runs LatentSync on the lip region
4. Ducks music under dialogue automatically (ffmpeg sidechain compressor)
5. Mixes everything and muxes back into MP4

---

## How this differs from Seedance native audio

| Aspect | Seedance 2.0 native | Our pipeline |
|---|---|---|
| Generation | Joint with video, single forward pass | Sequential, separate models |
| Sync precision | Frame-perfect | Frame-aligned (MMAudio sync module) |
| Lip-sync fidelity | Built-in, multilingual + dialect | LatentSync second pass, English-strongest |
| Music coherence | Trained on full multimodal corpus | Separate music model, may feel disjoint |
| Ambient + Foley + music + dialogue combined | Yes, single shot | Yes, but composed in post |
| Latency | One generation | Adds ~1–2 min per clip |

The composed result is **good enough that most viewers won't notice** for non-dialogue clips. Dialogue-heavy talking head is where Seedance's native lip-sync still has an edge.
