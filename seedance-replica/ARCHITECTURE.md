# Architecture — Seedance vs Replica

This document maps every published Seedance architectural detail to the closest open-source replica that runs on a 12 GB RTX 4070.

Sources: Seedance 1.0 technical report ([arxiv 2506.09113](https://arxiv.org/abs/2506.09113)), Seedance 1.5 Pro paper ([arxiv 2512.13507](https://arxiv.org/abs/2512.13507)), official ByteDance Seed page ([seed.bytedance.com/seedance2_0](https://seed.bytedance.com/en/seedance2_0)), Higgsfield Seedance 2.0 page ([higgsfield.ai/seedance/2.0](https://higgsfield.ai/seedance/2.0)).

> **Note on Seedance 2.0**: there is no public technical report at the time of writing. The arxiv ID 2604.14148 that appears in some search results is suspicious (encodes a date that has not occurred). What follows for 2.0 is derived from the product pages and inferred as an evolution of 1.5 Pro's published DB-DiT.

---

## 1. VAE (latent compression)

### Seedance 1.0 (published)
- Spatial × spatial × temporal compression: **(16, 16, 4)** — a single latent voxel encodes a 16×16-pixel × 4-frame chunk
- Latent channels: **C = 48**
- Note: "thin VAE decoder" — channel widths reduced for 2× decode speedup at no visible quality loss

### Seedance 1.5 Pro
- Inherits the video VAE; adds an **audio VAE** (specs not disclosed in abstract)

### Seedance 2.0
- Unknown publicly. Likely same family.

### Open replica
| Option | Compression | Latent C | Where |
|---|---|---|---|
| **Wan 2.2 standard VAE** | (8, 8, 4) — 256× spatial | 16 | `AutoencoderKLWan2` in Wan2.2 repo |
| **Wan 2.2 advanced VAE (TI2V-5B)** | (16, 16, 4) with patchification — 4096× | 16 | TI2V-5B model card |
| **LTX VAE** | (32, 32, 8) — 8192× | 128 | LTX-Video repo |

**Pick**: Wan 2.2 advanced VAE matches Seedance 1.0 exactly on stride (16×16×4). The latent-channel count differs (16 vs 48) — Seedance trades channels for capacity; Wan trades compression for compute. On a 4070, lower channel count is *good* — less VRAM.

---

## 2. DiT backbone

### Seedance 1.0 (published)
- **Decoupled spatial + temporal layers**:
  - Spatial layers: attention within each frame, also where text cross-attention happens
  - Temporal layers: window-partitioned attention across frames, global temporal receptive field
- **3D Multi-modal RoPE (MM-RoPE)**: positional encoding shared across vision and text tokens, allowing interleaved sequences for multi-shot
- Total parameter count: **not disclosed**, but inferred ~12–20 B based on Wan/Hunyuan peers

### Seedance 1.5 Pro (published)
- **Dual-Branch DiT (DB-DiT)**, **4.5 B parameters total**
- Two branches: video branch + audio branch, parallel
- **Cross-modal joint module** keeps them synchronized

### Seedance 2.0
- Public materials describe a "unified multimodal audio-video joint generation architecture" — likely an extension of DB-DiT with more parameters and more input modalities (text + image + audio + video, up to 12 reference assets)

### Open replica
| Option | Params | Architecture | Notes |
|---|---|---|---|
| **Wan 2.2 T2V-A14B** | 14 B (MoE) | DiT with cross-attn to UMT5-XXL, RoPE, AdaLN | SNR-based MoE: high-noise/low-noise expert switching |
| **Wan 2.2 I2V-A14B** | 14 B (MoE) | Same as above, image-conditioned | Best I2V open today |
| **Wan 2.2 TI2V-5B** | 5 B | Single dense DiT, advanced VAE | Easier on 12 GB, no MoE |
| **HunyuanVideo 1.5** | 8.3 B | DiT with dual-stream → single-stream | Tencent, 14 GB with offload |
| **LTX-Video 13B distilled** | 13 B | DiT, 8-step generation, no CFG | Fastest open option |

**Pick for 4070**:
- **Quality preset**: Wan 2.2 T2V-A14B in **GGUF Q5_K_M** (~6 GB on disk, ~6–8 GB VRAM with UMT5 offloaded to CPU)
- **Balanced preset**: Wan 2.2 TI2V-5B native fp16 (fits in 12 GB)
- **Fast preset**: LTX-Video 0.9.8-13B-distilled fp8 (~12 GB, real-time at 768×512)

---

## 3. Text encoder

### Seedance 1.0
- Fine-tuned **decoder-only LLM** (architecture not named in paper, but the Prompt Engineering component uses **Qwen2.5-14B**)

### Seedance 1.5 Pro / 2.0
- Multilingual, dialect-aware — likely Qwen2.5 family

### Open replica
- **UMT5-XXL** (multilingual T5) — what Wan 2.2 uses. ~9 GB on disk. **Offload to CPU RAM** on 12 GB GPUs; the text encoder runs once per prompt, not per step.
- Optional prompt expander: **Qwen2.5-7B** GGUF Q4_K_M (~5 GB) — mirrors Seedance's prompt engineering stage

---

## 4. Captioning model (for training data)

### Seedance 1.0
- **Tarsier2** — bilingual video understanding LLM, frozen visual encoder, fully fine-tuned LM
- Dense captions integrating dynamic (actions, camera) + static (character, scene) features

### Open replica
| Option | Strength | Notes |
|---|---|---|
| **ShareCaptioner-Video** | 4.8 M videos worth of training, dense captions | Closest open match to Tarsier2 |
| **AuroraCap** | Token-merge for efficiency, beats GPT-4V on Flickr30k CIDEr | Smaller, faster |
| **Tarsier-2 (open weights)** | Actual same family Seedance used | If weights released, use this |

**Pick**: ShareCaptioner-Video for the bulk captioning job; AuroraCap as a faster fallback.

---

## 5. Training stages

### Seedance 1.0 published progression
1. **Image pre-training** at low resolution (256 px)
2. **Video pre-training** at progressively higher resolution (up to 640 px)
3. **Joint T2V + I2V SFT** on curated high-quality pairs, multiple models trained then merged
4. **Multi-shot fine-tuning** with MM-RoPE
5. **RLHF** with three reward models:
   - Foundational (vision-language alignment)
   - Motion (artifact and motion quality)
   - Aesthetic (cinematography from keyframes)

### Seedance 1.5 Pro additions
- Audio pre-training on V+A pairs
- SFT on high-quality V+A
- RLHF with multi-dimensional reward stack

### Replica on 4070
You will **not** pretrain. You will **LoRA fine-tune** a pretrained Wan 2.2 base. Stages:
1. Caption your video corpus with ShareCaptioner-Video (1 min per 30 s clip, CPU+GPU)
2. Pre-process to webdataset format
3. Train LoRA rank-32 with musubi-tuner, fp8 + block swap, ~6–12 h for 4000 steps
4. Merge LoRA at generation time
5. (Optional) Distill your LoRA'd checkpoint with **CausVid** for 4-step inference

See [`docs/training_pipeline.md`](docs/training_pipeline.md) for exact commands.

---

## 6. Inference acceleration

### Seedance 1.0 published
- **TSCD** (trajectory segmented consistency distillation) → ~4× fewer steps
- System: kernel fusion, heterogeneous quantization + sparsity, adaptive hybrid parallelism
- Result: 5 s 1080p in **41.4 s on NVIDIA L20** (24 GB)

### Seedance 1.5 Pro
- "Acceleration framework boosts inference speed by **over 10×**" (details not published)

### Open replica
| Technique | Open implementation | Speedup |
|---|---|---|
| Consistency distillation | **CausVid** (DMD-based, 4-step) | 12–15× vs 50-step |
| Latent caching | **Δ-DiT, TeaCache** | 1.5–2× |
| FP8 weights | **`--fp8_scaled`** in musubi/ComfyUI | 1.5×, ~50% VRAM |
| Block swap | `--blocks_to_swap N` | enables 14 B on 12 GB |
| Torch compile | `torch.compile(mode='reduce-overhead')` | 1.3–1.8× |
| FA3 / Sage attention | xformers / sage-attention pkg | 1.2–1.5× |
| GGUF quantization | QuantStack Q4/Q5/Q6 | 50–70% VRAM |

Stack them all for the **quality** preset. The **fast** preset uses LTX-distilled which already has 8-step generation baked in.

---

## 7. Audio (Seedance 1.5 Pro / 2.0 only)

### Seedance
- Joint training inside the DB-DiT — audio and video share noise schedule, sampled together
- Native lip-sync with multilingual + dialect support

### Open replica
You can't joint-train without re-pretraining. **MMAudio** (CVPR 2025) is the best post-hoc V2A:
- Takes video + optional text prompt → generates synchronized 16 kHz audio
- Trained on Audioset, VGGSound, AudioCaps; multimodal joint training architecture
- Synchronization module aligns audio to video frames
- Runs on RTX 4070 in ~30 s for 5 s of audio

**Lip-sync specifically** is harder. For talking head:
- Use **Wav2Lip-HD** or **LatentSync** as a second-pass step on the generated face
- Or condition Wan-I2V on a portrait + use **Sonic** / **Hallo3** for talking-head animation

See [`docs/audio_pipeline.md`](docs/audio_pipeline.md).

---

## 8. Multi-shot / extended duration

### Seedance 2.0 (product spec)
- Up to **9 reference images + 3 video clips + 3 audio clips** in a single generation
- Native multi-shot with character consistency

### Open replica
- **Sequential generation**: generate shot 1, extract last frame, use as first frame of shot 2 via Wan I2V
- **Reference image conditioning**: use IP-Adapter / Redux-style adapters where available
- **Character consistency**: train a per-character LoRA, apply to every shot
- **Long video**: chain 5 s shots with crossfade; or use **FreeNoise** / **Gen-L-Video** style extension

Implemented in [`scripts/multishot.py`](scripts/multishot.py).

---

## 9. Summary mapping table

| Seedance subsystem | Closest open replica | Runs on 4070? |
|---|---|---|
| Causal video VAE (16,16,4)×48ch | Wan 2.2 advanced VAE (16,16,4)×16ch | ✅ |
| Decoupled spatio-temporal DiT | Wan 2.2 T2V-A14B (MoE) | ✅ (GGUF Q5) |
| MM-RoPE for multi-shot | Wan 2.2 RoPE + last-frame chain | ⚠️ approximate |
| Qwen2.5-14B prompt engineer | Qwen2.5-7B GGUF Q4 | ✅ |
| Tarsier2 captioner | ShareCaptioner-Video | ✅ |
| TSCD 4-step distillation | CausVid 4-step DMD | ✅ |
| RLHF reward stack | VBench scoring + manual SFT | ✅ (no RL) |
| DB-DiT joint audio-video | MMAudio post-hoc V2A | ✅ |
| Lip-sync multilingual | LatentSync / Sonic second pass | ✅ |
| Reference asset blending (up to 12) | IP-Adapter + multi-LoRA + first/last frame | ⚠️ approximate |
| 4K output | 720p native + Real-ESRGAN 2× | ✅ |
| 5-minute duration | Multi-shot chaining of 5 s segments | ⚠️ continuity drift |
| 60 fps | 24/30 fps native + RIFE 2× interpolation | ✅ |

---

For exact install steps and runnable commands, see [`REPLICATION_GUIDE.md`](REPLICATION_GUIDE.md).
