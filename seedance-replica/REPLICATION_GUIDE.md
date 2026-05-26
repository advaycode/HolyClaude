# Replication Guide — Clone to First Video in 90 Minutes

This is the practical walkthrough. If you just want to generate, follow steps 1–4. Steps 5–7 cover finetuning, distillation, and the audio pipeline.

**Target hardware**: RTX 4070 12 GB, 32 GB RAM, 200 GB free SSD, Windows 11 or Ubuntu 22.04.

---

## Step 1 — System prep (~10 min)

### Windows 11

```powershell
# Run from an admin PowerShell. Installs Python 3.11, git, CUDA 12.4, 7zip.
./scripts/install_4070.ps1
```

The script:
- Installs Python 3.11 via winget if missing
- Installs git, ffmpeg, 7zip
- Installs CUDA 12.4 if no CUDA found
- Creates `.venv` and installs PyTorch 2.5+cu124, xformers, sage-attention
- Clones ComfyUI + the GGUF custom node

### Ubuntu 22.04

```bash
chmod +x scripts/install_4070.sh
./scripts/install_4070.sh
```

### Verify
```powershell
python -c "import torch; print(torch.cuda.get_device_name(0), torch.cuda.is_available())"
# expected: NVIDIA GeForce RTX 4070 True
```

---

## Step 2 — Download weights (~25 min, 22 GB)

Pick a preset based on what you want first:

```powershell
# Balanced (recommended first run): Wan 2.2 TI2V-5B, fits natively in 12 GB
python scripts/download_models.py --preset balanced

# Fast: LTX 0.9.8 distilled, real-time-ish on 4070
python scripts/download_models.py --preset fast

# Quality: Wan 2.2 14B GGUF Q5_K_M + UMT5 offload
python scripts/download_models.py --preset quality

# All three (for benchmarking)
python scripts/download_models.py --preset all
```

Files land in `~/.cache/seedance-replica/models/` by default. Override with `--cache-dir`.

---

## Step 3 — First generation (~3 min)

```powershell
python scripts/generate.py \
  --preset balanced \
  --prompt "a samurai walks through cherry blossoms at dusk, soft pink petals drifting, cinematic shallow depth of field, slow dolly forward" \
  --duration 5 \
  --fps 24 \
  --resolution 720p \
  --seed 42 \
  --out out/first_clip.mp4
```

Expected wall time on 4070:
- Fast preset: 30–60 s
- Balanced preset: 2.5–4 min
- Quality preset: 6–10 min (with upscale)

Watch `nvidia-smi -l 1` in another shell — VRAM should peak around 9–11 GB.

### If you OOM
1. Lower resolution: `--resolution 480p`
2. Shorter duration: `--duration 3`
3. Switch preset: `--preset fast`
4. Add: `--blocks-to-swap 20` (offloads transformer blocks to CPU RAM)
5. Restart Python (CUDA fragmentation)

---

## Step 4 — Add audio (~30 s extra)

```powershell
python scripts/add_audio.py \
  --video out/first_clip.mp4 \
  --prompt "soft wind through trees, distant temple bell, ambient pads" \
  --out out/first_clip_with_audio.mp4
```

For dialogue / lip-sync:

```powershell
python scripts/add_audio.py \
  --video out/portrait.mp4 \
  --tts "Welcome to the future of video." \
  --lipsync \
  --voice eleven-rachel \
  --out out/talking_head.mp4
```

(Lip-sync uses LatentSync; you'll be prompted to download weights on first use.)

---

## Step 5 — Multi-shot sequence (~10 min for a 30 s clip)

```powershell
python scripts/multishot.py \
  --shots data/prompts/cyberpunk_sequence.json \
  --character-lora loras/aiko_v1.safetensors \
  --out out/cyberpunk_30s.mp4
```

`shots` JSON format:
```json
[
  {"prompt": "Aiko stands in a neon-lit Tokyo alley, rain reflecting signs", "duration": 5, "motion": "static"},
  {"prompt": "Aiko turns, hood up, walks toward the camera", "duration": 5, "motion": "dolly_in"},
  {"prompt": "Close-up of Aiko's face, neon flickering across her eyes", "duration": 5, "motion": "push_in"}
]
```

The script:
1. Generates shot 1
2. Extracts last frame
3. Feeds it as first-frame to Wan I2V for shot 2
4. Repeats
5. Concatenates with 6-frame crossfade
6. Optionally runs MMAudio on the whole concat for ambient continuity

---

## Step 6 — Train a style LoRA (~6 h)

Drop 30–200 short clips (5–15 s each) into `data/my_clips/`. Then:

```powershell
# Step 6a: caption everything
python scripts/caption_video.py \
  --input data/my_clips/ \
  --output data/my_clips_captions.json \
  --captioner share-captioner-video

# Step 6b: train
python scripts/train_lora.py \
  --data data/my_clips/ \
  --captions data/my_clips_captions.json \
  --base wan2.2-ti2v-5b \
  --rank 32 \
  --steps 4000 \
  --lr 1e-4 \
  --batch-size 1 \
  --fp8 \
  --blocks-to-swap 20 \
  --output loras/my_style_v1.safetensors
```

VRAM usage: ~11 GB peak. Throughput: ~1.0 step/s, so 4000 steps ≈ 67 min/epoch; figure 6–12 h depending on dataset size.

Use the LoRA at generation time:
```powershell
python scripts/generate.py --preset balanced --lora loras/my_style_v1.safetensors --lora-weight 0.8 --prompt "..."
```

---

## Step 7 — Distill for fast inference (optional, ~12 h)

If you've trained a style LoRA and want real-time generation in that style, distill it with CausVid:

```powershell
python scripts/distill_causvid.py \
  --teacher loras/my_style_v1.safetensors \
  --base wan2.2-ti2v-5b \
  --steps 8000 \
  --output loras/my_style_v1_4step.safetensors
```

Then generate with 4 steps instead of 30:
```powershell
python scripts/generate.py --preset balanced --lora loras/my_style_v1_4step.safetensors --num-steps 4 --prompt "..."
```

Expect 5–10× speedup with minor quality loss.

---

## Common issues

| Symptom | Cause | Fix |
|---|---|---|
| `OOM at decode` | VAE decode spike | Add `--tiled-decode` (slower, 4 GB less peak) |
| Black frames | NaN in fp8 path | Use `--fp8-scaled` not `--fp8`; or drop to fp16 |
| `torch._C` import error | Wrong PyTorch/CUDA pair | Reinstall via `install_4070.ps1 --force` |
| Generation looks like 2020 AI | Wrong VAE loaded | Check log for `Wan2_2_VAE.safetensors`; download_models.py re-fetches |
| Sage attention not used | Not installed for your torch | `pip install sageattention --no-build-isolation` |
| Stutter / hitching at end | RAM swap | Close Chrome; add `--blocks-to-swap 30` to push more to RAM |

---

## What "EXACTLY like Seedance 2.0" honestly means here

The output of this stack will be **visually compelling, prompt-faithful, motion-stable** clips. It will *not* be indistinguishable from Higgsfield Seedance 2.0 output. The gap on a head-to-head identical prompt:

- **Motion physics**: Seedance handles fluid/cloth/skeletal motion better. Replica is good, not best-in-class.
- **Long-shot consistency**: Seedance keeps a character on-model for 60 s. Replica drifts after ~10 s without strong LoRA + multi-shot chaining.
- **Lip-sync nativity**: Seedance generates audio + lip motion jointly. Replica uses two separate models — close, but cracks visible in close-ups.
- **Prompt comprehension**: Seedance has a fine-tuned Qwen2.5-14B prompt engineer. Replica uses base UMT5; short prompts work, long compositional prompts may lose pieces.

What you get back: **everything is local, free, fully tunable, and your dataset never leaves your machine.**

---

Next: [`docs/training_pipeline.md`](docs/training_pipeline.md) for deeper finetuning, [`docs/inference_pipeline.md`](docs/inference_pipeline.md) for ComfyUI integration.
