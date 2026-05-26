# Inference Pipeline

How a prompt becomes an MP4. Two paths supported: this repo's CLI (`scripts/generate.py`) and ComfyUI (drop-in workflows in `configs/comfyui_workflows/`).

---

## Path A — CLI

### Single prompt, balanced preset

```powershell
python scripts/generate.py \
  --preset balanced \
  --prompt "a samurai walks through cherry blossoms at dusk" \
  --duration 5 --fps 24 --resolution 720p \
  --seed 42 \
  --out out/clip.mp4
```

### With image conditioning (I2V)

```powershell
python scripts/generate.py \
  --preset balanced \
  --image reference/portrait.png \
  --prompt "the subject slowly turns and smiles, soft window light" \
  --duration 5 --out out/portrait_motion.mp4
```

### With style LoRA

```powershell
python scripts/generate.py \
  --preset balanced \
  --lora loras/cinematic_anime_v3.safetensors --lora-weight 0.85 \
  --prompt "a cyberpunk rooftop at night, rain, neon" \
  --duration 5 --out out/cyber.mp4
```

### Fast preset (LTX distilled)

```powershell
python scripts/generate.py \
  --preset fast \
  --prompt "a hummingbird hovers near a red flower, slow motion" \
  --duration 4 --resolution 768x512 --out out/hummingbird.mp4
```

Generates in ~30 s. Lower quality than balanced but real-time-ish.

### Quality preset (Wan 14B GGUF, full pipeline)

```powershell
python scripts/generate.py \
  --preset quality \
  --prompt "..." \
  --duration 5 --resolution 480p \
  --upscale 2x \
  --interpolate 60fps \
  --out out/hero_shot.mp4
```

The `--upscale 2x` runs Real-ESRGAN; `--interpolate 60fps` runs RIFE.

### Common flags

| Flag | Effect |
|---|---|
| `--num-steps N` | Override default sampler steps (30 balanced, 8 fast, 4 if using CausVid LoRA) |
| `--cfg N` | Classifier-free guidance scale (Wan default 6.0; LTX needs 1.0) |
| `--sampler X` | `dpmpp_2m_sde`, `euler`, `unipc` |
| `--scheduler X` | `karras`, `simple` |
| `--prompt-expander qwen2.5-7b` | Pre-expand prompt with local LLM |
| `--negative "..."` | Negative prompt |
| `--blocks-to-swap N` | RAM offload count (0–40); higher = lower VRAM, slower |
| `--tiled-decode` | VAE decode in tiles (drops decode VRAM ~4 GB) |
| `--save-frames` | Also dump individual frames as PNG sequence |
| `--metadata` | Write generation metadata as MP4 sidecar JSON |

---

## Path B — ComfyUI

For visual workflows / node-based control.

### Install (already done by `install_4070.ps1`)

ComfyUI is cloned to `~/ComfyUI`. Custom nodes installed:
- ComfyUI-GGUF (loads Wan/Hunyuan GGUFs)
- ComfyUI-VideoHelperSuite (mp4 mux, frame extract)
- ComfyUI-MMAudio (V2A nodes)
- ComfyUI-LatentSync (lip-sync node)
- ComfyUI-AdvancedLoRA (per-block LoRA weighting)

### Workflow files

Drop these into `~/ComfyUI/user/default/workflows/`:

| File | Purpose |
|---|---|
| `t2v_wan22_gguf.json` | Text-to-video, Wan 2.2 14B GGUF Q5, 720p |
| `i2v_wan22_gguf.json` | Image-to-video, Wan 2.2 14B GGUF |
| `t2v_ltx_realtime.json` | LTX distilled, 8 steps, 768×512 |
| `t2v_wan22_5b.json` | Wan 2.2 TI2V-5B native fp16 |
| `audio_mmaudio.json` | MMAudio V2A post-process |
| `multishot_chained.json` | 3-shot chained sequence, last-frame conditioning |
| `lipsync_latentsync.json` | Talking-head lip-sync |
| `upscale_rife_resrgan.json` | 720p→1080p + 24→60 fps |
| `full_pipeline.json` | Everything end-to-end, single workflow |

Open ComfyUI at `http://localhost:8188`, File → Load → select a workflow JSON.

### ComfyUI launch

```powershell
cd ~/ComfyUI
python main.py --listen 127.0.0.1 --port 8188 --highvram   # adjust to --normalvram or --lowvram if OOM
```

---

## Preset detail

### Fast — LTX-Video 0.9.8 distilled

| Setting | Value |
|---|---|
| Model | `ltxv-13b-0.9.8-distilled-fp8` |
| VAE | LTX VAE |
| Text encoder | T5-XXL |
| Resolution | 768×512 default (up to 1216×704) |
| Frames | 97 (4 s @ 24 fps) up to 257 (10 s) |
| Sampling steps | 8 |
| CFG | 1.0 (no CFG) |
| VRAM peak | ~9 GB |
| Wall time @ 4 s | ~30–45 s |

Best for: quick iteration, prompt testing, generating drafts before committing to quality preset.

### Balanced — Wan 2.2 TI2V-5B

| Setting | Value |
|---|---|
| Model | `Wan-AI/Wan2.2-TI2V-5B` (native fp16) |
| VAE | Wan 2.2 advanced VAE |
| Text encoder | UMT5-XXL (offloaded to CPU) |
| Resolution | 1280×720 default |
| Frames | 81 (3.4 s) up to 121 (5 s) |
| Sampling steps | 30 |
| Sampler | `dpmpp_2m_sde` + `karras` |
| CFG | 6.0 |
| VRAM peak | ~10 GB |
| Wall time @ 5 s | 2.5–4 min |

Best for: most use cases. Solid quality without GGUF fiddling.

### Quality — Wan 2.2 T2V-A14B GGUF Q5_K_M

| Setting | Value |
|---|---|
| Model | `QuantStack/Wan2.2-T2V-A14B-GGUF` (Q5_K_M, ~6 GB) |
| VAE | Wan 2.2 standard VAE |
| Text encoder | UMT5-XXL (offloaded) |
| Resolution | 832×480 native, upscale to 1080p |
| Frames | 81 |
| Sampling steps | 30 |
| Sampler | `unipc` (works well with MoE) |
| CFG | 6.0 |
| VRAM peak | ~11 GB (with `--blocks-to-swap 20`) |
| Wall time @ 5 s | 6–10 min (with upscale) |

Best for: hero shots, final renders, anything where quality > iteration speed.

---

## Performance tuning checklist

If generation is slow or OOMing:

1. **Check VRAM at peak**: `nvidia-smi -l 1` — should be 9–11 GB at the diffusion step
2. **Lower resolution**: 720p → 480p drops VRAM by ~40%
3. **Lower frame count**: 81 → 49 drops VRAM by ~30%
4. **Raise `--blocks-to-swap`**: each block = ~150 MB VRAM saved, ~50 ms added per step
5. **Enable `--tiled-decode`**: drops VAE decode peak by ~4 GB
6. **Use GGUF**: Q5_K_M cuts model VRAM ~60% vs fp16
7. **Use `--fp8-scaled`** if not already
8. **Install sage-attention**: `pip install sageattention` (1.3× speedup on Ada)
9. **Try torch.compile**: `--torch-compile` (first call slow, subsequent fast)
10. **Close Chrome, Discord**: every GB of system RAM matters when blocks-swap is high

---

## Quality tuning checklist

If output looks bad:

1. **Bad prompts**: add camera (35mm, dolly, push-in), lighting (golden hour, soft window light), composition (close-up, wide shot), mood
2. **Wrong CFG**: too low → ignores prompt, too high → oversaturated; sweet spot for Wan is 5–7
3. **Wrong sampler**: try `dpmpp_2m_sde` vs `unipc` vs `euler_a`
4. **LoRA weight wrong**: 0.8 is usually the sweet spot; >1.0 distorts
5. **Resolution mismatch**: train resolution should match inference; LoRAs trained at 720p don't always work at 480p
6. **Seed lottery**: try 4–5 seeds before judging a prompt
7. **Negative prompt missing**: add "blurry, low quality, distorted, warped, choppy motion"
8. **Use prompt expander**: `--prompt-expander qwen2.5-7b` adds the missing cinematography vocabulary
9. **Try a different base**: balanced → quality often fixes structural issues; fast preset is for iteration only

---

## Comparing your output to Seedance

Quick A/B:

```powershell
# Your version
python scripts/generate.py --preset quality --prompt "{X}" --seed 42 --out out/mine.mp4

# Send same prompt to Seedance via Higgsfield API (~$0.25)
python scripts/seedance_compare.py --prompt "{X}" --seed 42 --out out/seedance.mp4

# Side-by-side
python scripts/side_by_side.py --left out/mine.mp4 --right out/seedance.mp4 --out compare.mp4
```

(Requires `HIGGSFIELD_API_KEY` in `.env`.)

This is how you know where the gap actually is on *your* prompts and adjust LoRA / config accordingly.
