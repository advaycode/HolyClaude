<div align="center">

# Seedance-Replica

**Open-source path to near-Seedance-2.0 quality video generation on a single RTX 4070 (12 GB VRAM).**

[![Python](https://img.shields.io/badge/Python-3.10%2B-3776ab?style=flat-square&logo=python&logoColor=white)](https://python.org)
[![CUDA](https://img.shields.io/badge/CUDA-12.1%2B-76b900?style=flat-square&logo=nvidia&logoColor=white)](https://developer.nvidia.com/cuda-downloads)
[![GPU](https://img.shields.io/badge/GPU-RTX_4070_12GB-22c55e?style=flat-square)](https://www.nvidia.com/en-us/geforce/graphics-cards/40-series/rtx-4070-family/)
[![ComfyUI](https://img.shields.io/badge/ComfyUI-compatible-orange?style=flat-square)](https://github.com/comfyanonymous/ComfyUI)
[![License](https://img.shields.io/badge/License-MIT-22c55e?style=flat-square)](../LICENSE)

</div>

---

## Reality check (read this first)

Seedance 2.0 is a proprietary ByteDance model. It was trained on what is almost certainly thousands of H100/H800 GPUs over weeks-to-months on petabytes of curated video. Each parameter, dataset hour, and training-stage detail is a trade secret. **A single RTX 4070 (12 GB) cannot 1:1 replicate it.**

What this repo *does* deliver:

| Goal | Achievable on 4070? | How |
|---|---|---|
| Generate 720p text-to-video clips | **Yes** | Wan 2.2 14B GGUF Q5 + UMT5 offload |
| Generate 1080p clips | **Yes (slow, upscaled)** | 720p native + Real-ESRGAN 1.5×–2× |
| Image-to-video | **Yes** | Wan 2.2 I2V GGUF |
| Multi-shot continuity | **Approximate** | Last-frame conditioning + sequential gen |
| Synchronized audio | **Yes** | MMAudio (V2A) post-hoc, not native joint |
| Real-time generation | **Limited** | LTX-Video 0.9.8 distilled, 8 steps, lower quality |
| LoRA finetune your own style | **Yes** | musubi-tuner, ~12 GB VRAM, ~6 h per LoRA |
| Train a foundation model from scratch | **No** | Needs ~1000× more compute |
| Hit Seedance Elo 1,269 on T2V | **No** | Realistic ceiling is ~Wan 2.2 baseline + LoRA polish |

The honest pitch: **you get Seedance-1.0-territory output quality with Seedance-style workflow ergonomics, on hardware that fits under your desk.**

Full gap analysis: [`docs/reality_check.md`](docs/reality_check.md).

---

## What's inside

```
seedance-replica/
├── README.md                       ← you are here
├── ARCHITECTURE.md                 ← Seedance specs + open replica mapping
├── REPLICATION_GUIDE.md            ← end-to-end clone-to-first-video walkthrough
├── docs/
│   ├── reality_check.md            ← H100-cluster vs 4070, honest
│   ├── seedance_specs.md           ← every number we know from 1.0 / 1.5 Pro / 2.0
│   ├── component_mapping.md        ← table: Seedance subsystem → open replica
│   ├── training_pipeline.md        ← data → caption → SFT → LoRA → distill
│   ├── inference_pipeline.md       ← ComfyUI workflow + CLI usage
│   └── audio_pipeline.md           ← MMAudio post-hoc V2A
├── configs/
│   ├── 4070_fast.yaml              ← LTX-distilled, 5 s @ 768×512, ~30 s gen time
│   ├── 4070_balanced.yaml          ← Wan 2.2 TI2V-5B, 5 s @ 720p, ~3 min gen time
│   ├── 4070_quality.yaml           ← Wan 2.2 14B GGUF Q5, 5 s @ 480p→1080p upscale
│   └── comfyui_workflows/          ← drop-in JSON workflow files
├── scripts/
│   ├── install_4070.ps1            ← Windows one-shot installer
│   ├── install_4070.sh             ← Linux equivalent
│   ├── download_models.py          ← pulls all GGUFs + VAE + UMT5 + MMAudio
│   ├── generate.py                 ← CLI: text/image → video
│   ├── caption_video.py            ← ShareCaptioner-Video or AuroraCap
│   ├── train_lora.py               ← musubi-tuner wrapper, 4070 presets
│   ├── multishot.py                ← N shots with last-frame chaining
│   └── add_audio.py                ← MMAudio V2A wrapper
├── data/prompts/
│   └── seedance_style.md           ← prompt templates that elicit Seedance aesthetic
├── benchmarks/
│   └── seedvidebench_lite.py       ← subset of SeedVideoBench eval
└── requirements.txt
```

---

## Quickstart

> **First-time user?** Open [`RISHI_START_HERE.md`](RISHI_START_HERE.md) instead — it's a friendlier walkthrough with what-to-expect at every step.

```powershell
# 1. clone (you already did this if you're reading the file)
git clone -b seedance-replica https://github.com/advaycode/HolyClaude
cd HolyClaude/seedance-replica

# 2. install (Windows, run as user, ~15 min)
./scripts/install_4070.ps1

# 3. download model weights (~22 GB; coffee break)
python scripts/download_models.py --preset balanced

# 4. generate your first clip
python scripts/generate.py \
  --preset balanced \
  --prompt "a samurai walks through cherry blossoms at dusk, cinematic, slow dolly" \
  --duration 5 --out out/samurai.mp4

# 5. add audio
python scripts/add_audio.py --video out/samurai.mp4 --prompt "soft wind, distant temple bell"

# 6. (optional) train a style LoRA
python scripts/train_lora.py --data data/my_clips/ --steps 4000 --rank 32
```

---

## Compared to using Seedance 2.0 directly

| | Higgsfield Seedance 2.0 | This repo on RTX 4070 |
|---|---|---|
| Cost | $25–$95/mo subscription, per-second billing on Volcano | $0 after hardware |
| Privacy | Cloud-hosted, prompts logged | 100% local |
| Resolution | 4K up to 5 min | 720p–1080p, 5–10 s per shot |
| Audio | Native joint generation | Post-hoc MMAudio (still synced) |
| Style control | Limited | Full LoRA training on your data |
| Speed | ~30 s for 5 s clip | 30 s (fast) – 3 min (balanced) – 8 min (quality) |
| Multi-shot | 12 reference assets, frame-precise | Sequential with last-frame chaining |

Use Seedance 2.0 when you need cutting-edge quality and have budget. Use this repo when you need privacy, control, offline operation, or zero marginal cost per video.

---

## Credits & sources

This repo stands on the shoulders of:

- **ByteDance Seed** — Seedance 1.0 ([arxiv 2506.09113](https://arxiv.org/abs/2506.09113)), Seedance 1.5 Pro ([arxiv 2512.13507](https://arxiv.org/abs/2512.13507))
- **Wan-Video / Tongyi Wanxiang** — Wan 2.2 base ([github](https://github.com/Wan-Video/Wan2.2))
- **Lightricks** — LTX-Video 0.9.8 distilled ([HF](https://huggingface.co/Lightricks/LTX-Video-0.9.8-13B-distilled))
- **hkchengrex et al.** — MMAudio ([github](https://github.com/hkchengrex/MMAudio))
- **kohya-ss** — musubi-tuner ([github](https://github.com/kohya-ss/musubi-tuner))
- **tianweiy et al.** — CausVid 4-step distillation ([github](https://github.com/tianweiy/CausVid))
- **QuantStack** — Wan 2.2 GGUF quantizations ([HF](https://huggingface.co/QuantStack/Wan2.2-T2V-A14B-GGUF))
- **ShareGPT4Video** team — video captioning ([github](https://github.com/ShareGPT4Omni/ShareGPT4Video))

---

<div align="center">

*MIT License · Built by [advaycode](https://github.com/advaycode) — part of [HolyClaude](../README.md)*

</div>
