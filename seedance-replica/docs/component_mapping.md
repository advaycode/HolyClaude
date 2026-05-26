# Component Mapping — Seedance → Open Replica

Side-by-side, every Seedance subsystem mapped to the open-source piece we use, with the rationale for each choice.

## At a glance

| Seedance subsystem | Our replica | Why this one |
|---|---|---|
| Video VAE (16,16,4)×48ch | Wan 2.2 advanced VAE (16,16,4)×16ch | Identical spatial+temporal stride; smaller channel count is better for 12 GB |
| Decoupled spatio-temporal DiT | Wan 2.2 T2V-A14B (MoE DiT) | Closest open architecture family + scale; GGUF-quantizable |
| Text encoder | UMT5-XXL (multilingual T5) | Wan ships with this; multilingual; offload-friendly |
| Prompt engineer | Qwen2.5-7B GGUF Q4 | Same family as Seedance's Qwen2.5-14B, scaled to 4070 |
| Captioning (training prep) | ShareCaptioner-Video | Open, dense captions, trained on 4.8 M video corpus |
| Multi-shot interleaved tokens | Wan I2V last-frame chaining | MM-RoPE not open; this approximates |
| Distillation | CausVid 4-step DMD | Open implementation of consistency distillation |
| RLHF reward stack | VBench scoring + manual SFT | Full RLHF requires reward model training we can't afford |
| Audio joint generation | MMAudio V2A (post-hoc) | Best open V2A, syncs to video frames |
| Lip-sync | LatentSync (second pass) | SOTA open lip-sync |
| Character consistency | Per-character LoRA + reference frame | IP-Adapter alternative |
| Long video | Sequential shots + crossfade | Replaces Seedance "long-form continuity" |
| 1080p / 4K | 720p native + Real-ESRGAN 1.5×–2× | Real-ESRGAN keeps detail without re-diffusion |
| 60 fps | 24/30 fps + RIFE 2× | RIFE 4.x is fast and clean |

---

## Detailed swaps

### Swap 1 — VAE

**Seedance** has a custom causal video VAE that compresses to a (4, 16, 16) latent with 48 channels. The decoder was trimmed for inference speed.

**Replica**: **Wan 2.2 advanced VAE** (the one shipped with the TI2V-5B model card). Same (16, 16, 4) stride, 16 latent channels. Difference:
- 16 vs 48 channels means our latents carry less information per voxel. The DiT compensates.
- The decoder is heavier; we use ComfyUI's tiled decode for low-VRAM operation.

Loaded from `Wan-AI/Wan2.2-TI2V-5B` (HF) → `vae/Wan2_2_VAE.safetensors`.

---

### Swap 2 — DiT backbone

**Seedance** uses decoupled spatial + temporal blocks with text cross-attention in spatial blocks, plus 3D MM-RoPE.

**Replica**: **Wan 2.2 T2V-A14B**. Same idea: DiT with RoPE, AdaLN, cross-attention to UMT5. Wan 2.2 adds MoE expert switching (high-noise vs low-noise) which Seedance doesn't appear to use.

We use the **GGUF Q5_K_M quantization** from `QuantStack/Wan2.2-T2V-A14B-GGUF` to fit in 12 GB.

Trade-offs:
- Q5_K_M ≈ 5.6 bits per weight, minor quality loss vs fp16
- The MoE adds variance — sometimes the wrong expert fires; usually fine
- No MM-RoPE → multi-shot is via image conditioning, not native

---

### Swap 3 — Text encoder

**Seedance** fine-tunes a decoder-only LLM for text conditioning. Architecture not disclosed.

**Replica**: **google/umt5-xxl** as shipped with Wan 2.2. ~9 GB on disk, loaded once per prompt, offloaded to CPU between inferences. Tokenizer is sentencepiece-multilingual.

If you want a Seedance-style **prompt expansion** step before the encoder:
```python
# scripts/generate.py supports this:
--prompt-expander qwen2.5-7b
```
Loads a Qwen2.5-7B GGUF, expands the prompt with a fixed system message ("rewrite as a detailed cinematic shot description with motion, lighting, lens, mood"), then feeds the expansion to UMT5.

---

### Swap 4 — Captioning

**Seedance** uses Tarsier2. Tarsier2's open weights exist but the bilingual dataset Seedance used to fine-tune doesn't.

**Replica**: **ShareCaptioner-Video** from the ShareGPT4Video project. Trained on 4.8 M videos with GPT-4V-style dense captions. Strong on actions, scene composition, character description. Open weights on HF.

Fallback: **AuroraCap** if you want speed (smaller, token-merged).

Used in `scripts/caption_video.py` for the training-data prep step.

---

### Swap 5 — Distillation

**Seedance** uses TSCD (trajectory segmented consistency distillation) for ~4× step reduction.

**Replica**: **CausVid** — also a consistency distillation approach, also collapses 50-step diffusion to 4 steps. Open code at [github.com/tianweiy/CausVid](https://github.com/tianweiy/CausVid). The student model can be initialized from the teacher's ODE trajectories; we apply CausVid to LoRA'd Wan checkpoints in `scripts/distill_causvid.py`.

---

### Swap 6 — RLHF reward stack

**Seedance** has three reward models (Foundational, Motion, Aesthetic) and runs RL on top of SFT.

**Replica**: We don't do full RLHF (it requires running the reward model loop alongside the generator — infeasible on 4070). Instead:
- **VBench** for automated scoring (16-dimension benchmark)
- **Subjective preference SFT**: generate two variants per prompt, manually pick the better, fine-tune the LoRA on the preferred set
- For aesthetic: use **LAION-Aesthetic v2** classifier as a single reward signal in a small DPO loop if you really want RL

This is the biggest quality gap. Seedance's RLHF buys them a lot of polish.

---

### Swap 7 — Joint audio-video

**Seedance 1.5 Pro / 2.0** generates audio and video in a single forward pass through the DB-DiT, sharing noise schedules.

**Replica**: **MMAudio** runs after video generation. It's a multimodal model trained on Audioset, VGGSound, AudioCaps that takes video + optional text → 16 kHz synchronized audio. The sync module aligns by frame.

What you lose:
- Audio and video share information at every step in Seedance; ours don't
- For human speech / lip-sync, this matters (use LatentSync second pass)
- For ambient / Foley / music, it's nearly indistinguishable

---

### Swap 8 — Lip-sync

**Seedance** generates speech and lip motion together with multilingual/dialect support.

**Replica**: Generate video first (no speech), then:
1. Run TTS (ElevenLabs API or local Piper TTS) to get the audio
2. Run **LatentSync** to re-render the mouth region matching the audio
3. Composite

`scripts/add_audio.py --lipsync` does this end-to-end.

---

### Swap 9 — Reference asset blending

**Seedance 2.0** takes up to 12 reference assets (9 image + 3 video + 3 audio) in one generation. The model attends over all of them.

**Replica**: This is the hardest to match. We do:
- Up to 4 image references via **IP-Adapter** (if a Wan-compatible IP-Adapter is available; otherwise we use CLIP image embedding injection)
- Video references via **first frame + last frame conditioning** (extracted from each)
- Audio references via MMAudio with audio-conditioning hints
- Character consistency via **per-character LoRA** loaded with adjustable weight

Implemented (loosely) in `scripts/multishot.py`.

---

### Swap 10 — Resolution & frame rate

**Seedance 2.0** outputs up to 4K @ 60 fps (per marketing).

**Replica**:
- **Resolution**: native 720p (1280×720) via Wan 2.2. For 1080p, run **Real-ESRGAN x2** post-hoc on each frame. For 4K, chain Real-ESRGAN x2 → x2 (with frame-consistency tricks).
- **Frame rate**: native 24 fps (Wan default) or 30 fps. For 60 fps, run **RIFE 4.x** for 2× temporal interpolation.

Both are quick (a few seconds per second of video) and run in 4–6 GB VRAM.

---

## Component dependency graph

```
                 ┌────────────────────┐
                 │  user prompt + img  │
                 └─────────┬──────────┘
                           │
                ┌──────────▼───────────┐
                │ Qwen2.5-7B expander  │ (optional)
                └──────────┬───────────┘
                           │
                ┌──────────▼───────────┐
                │      UMT5-XXL        │ (text encoder, CPU-offloaded)
                └──────────┬───────────┘
                           │
   ┌───────────────────────▼────────────────────────┐
   │       Wan 2.2 14B GGUF DiT  +  LoRAs           │
   │     (GPU, GGUF Q5, blocks-swap to RAM)          │
   └───────────────────────┬────────────────────────┘
                           │  latents
                ┌──────────▼───────────┐
                │  Wan 2.2 VAE decode  │ (tiled)
                └──────────┬───────────┘
                           │  frames
            ┌──────────────┼──────────────┐
            │              │              │
       ┌────▼─────┐  ┌─────▼────┐  ┌─────▼──────┐
       │  RIFE    │  │ R-ESRGAN │  │  MMAudio   │
       │ (60 fps) │  │  (1080p) │  │   (V2A)    │
       └────┬─────┘  └─────┬────┘  └─────┬──────┘
            │              │              │
            └──────┐  ┌────┴──────┐  ┌────┘
                   │  │           │  │
                ┌──▼──▼──┐    ┌───▼──▼──┐
                │ ffmpeg │    │LatentSync│ (optional)
                │ mux    │    │ (lip)    │
                └────────┘    └──────────┘
                     │              │
                     └──────┬───────┘
                            │
                     ┌──────▼──────┐
                     │ final mp4   │
                     └─────────────┘
```
