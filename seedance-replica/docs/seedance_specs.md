# Seedance Specs — Everything We Know

Compiled from primary sources only. Where the published material doesn't disclose a number, this doc says "not disclosed" rather than guessing.

## Seedance 1.0 (June 2025)

**Sources**:
- arxiv [2506.09113](https://arxiv.org/abs/2506.09113)
- ByteDance Seed blog post: [Tech Report of Seedance 1.0](https://seed.bytedance.com/en/blog/tech-report-of-seedance-1-0-is-now-publicly-available)

### Architecture

| Component | Spec |
|---|---|
| VAE compression | spatial × spatial × temporal = (16, 16, 4) |
| VAE latent channels | C = 48 |
| VAE decoder optimization | "thin" decoder, reduced channel widths, 2× decode speedup |
| DiT structure | decoupled spatial + temporal transformer blocks |
| Spatial blocks | within-frame attention + text cross-attention |
| Temporal blocks | window-partitioned cross-frame attention, global temporal receptive field |
| Positional encoding | 3D MM-RoPE (Multi-modal RoPE) shared across visual + text tokens |
| Total parameters | **not disclosed** in paper |

### Text & prompt path

| Component | Spec |
|---|---|
| Text encoder | fine-tuned decoder-only LLM (architecture not named) |
| Prompt engineering | Qwen2.5-14B fine-tuned for prompt rewriting |
| Captioning model (data prep) | Tarsier2 (bilingual, dense action+scene captions) |

### Training stages

| Stage | What | Resolution / details |
|---|---|---|
| 1. Image pretrain | 2D DiT warm-up | 256 px |
| 2. T2V pretrain | Add temporal blocks | progressive 256 → 640 px |
| 3. Joint SFT | T2V + I2V on high-quality pairs | high-res, multiple specialists trained then merged |
| 4. Multi-shot | MM-RoPE enables interleaved seq | continued from SFT |
| 5. RLHF | Three reward models | Foundational (V-L), Motion, Aesthetic |

### Training data

- "Multi-source data curation" with augmentation
- Total hours: **not disclosed**

### Inference acceleration

| Technique | Effect |
|---|---|
| TSCD (trajectory segmented consistency distillation) | ~4× fewer steps |
| Kernel fusion | operator-level optimization |
| Heterogeneous quantization + sparsity | mixed-precision serving |
| Adaptive hybrid parallelism | tensor + pipeline split |
| **Result** | 5 s @ 1080p in **41.4 s on NVIDIA L20** |

### Public benchmarks

- Ranked **#1** on Artificial Analysis text-to-video Elo at release
- Ranked **#1** on Artificial Analysis image-to-video Elo at release

---

## Seedance 1.5 Pro (December 2025)

**Sources**:
- arxiv [2512.13507](https://arxiv.org/abs/2512.13507)
- ByteDance Seed page: [Seedance 1.5 Pro publications](https://seed.bytedance.com/en/public_papers/seedance-1-5-pro-a-native-audio-visual-joint-generation-foundation-model)

### Architecture

| Component | Spec |
|---|---|
| Architecture family | Dual-Branch Diffusion Transformer (DB-DiT) |
| Total parameters | **4.5 B** |
| Branches | Video branch + Audio branch, parallel |
| Cross-modal module | Joint module synchronizing the two branches |
| Audio VAE specs | **not disclosed** |
| Video VAE specs | inherited from 1.0 family (assumed) |

### Capabilities

- Precise multilingual + dialect lip-syncing
- Dynamic cinematic camera control
- Enhanced narrative coherence
- Audio-video joint sampling in a single pass

### Training

- Multi-stage data pipeline (specifics not in abstract)
- SFT on high-quality V+A pairs
- RLHF with **multi-dimensional reward models** (count not specified)

### Inference

- Acceleration framework yields **>10× inference speedup** over base
- Hardware / latency targets not disclosed in abstract

---

## Seedance 2.0 (February 2026)

**Sources**:
- ByteDance Seed product page: [seed.bytedance.com/seedance2_0](https://seed.bytedance.com/en/seedance2_0)
- Higgsfield product page: [higgsfield.ai/seedance/2.0](https://higgsfield.ai/seedance/2.0)
- Volcano Engine release news: [aibase.com news](https://news.aibase.com/news/26788)
- ⚠️ **No public technical report** at time of writing.
- ⚠️ The arxiv ID `2604.14148` that surfaces in search results appears to be either misindexed or fabricated; treat any architectural numbers attributed to it with skepticism.

### Confirmed product specs

| Spec | Value | Source |
|---|---|---|
| Input modalities | text + image + audio + video | ByteDance Seed page |
| Max reference assets per generation | 12 (9 images + 3 video + 3 audio) | Higgsfield page |
| Max clip duration | 15 s per shot | Higgsfield page |
| Native audio | yes, joint generation | both |
| Release | Volcano Engine, Feb 12, 2026; Higgsfield same period | Volcano news |
| Benchmark | leads SeedVideoBench-2.0 on T2V, I2V, multimodal | ByteDance |

### Unconfirmed / blog-sourced claims (treat as marketing)

These appear in third-party blog posts but are NOT in primary ByteDance sources:

- "4K Ultra HD output"
- "60 fps"
- "Up to 5 minutes via Long-Form Continuity"
- "Latent Space Anchoring"
- "Physics-Aware Rendering"
- "GPT Image 2 integration / Suno AI integration"

Some of these may be true; others look like SEO bait. Don't architect a replica around them without independent confirmation.

### Architecture (inferred)

Given continuity from 1.5 Pro:
- Likely DB-DiT extension
- Likely larger than 4.5 B (probably 7–13 B range)
- Likely supports interleaved multimodal token sequences (extension of MM-RoPE)
- Likely uses the same / improved video VAE family
- Likely uses an upgraded prompt engineering model (Qwen2.5 → 3 family?)

**None of the above is verified.** When the technical report drops, update this doc.

---

## SeedVideoBench-2.0

ByteDance's in-house eval. Three dimensions:
1. Text-to-video
2. Image-to-video
3. Multimodal (text + image + audio + video inputs)

Open replica: We use a subset in [`benchmarks/seedvidebench_lite.py`](../benchmarks/seedvidebench_lite.py) that overlaps with VBench prompts so results are comparable to the open community.

---

## Cross-reference table

| Aspect | 1.0 | 1.5 Pro | 2.0 |
|---|---|---|---|
| Params | not disclosed | 4.5 B | unknown |
| Audio | no | yes (native) | yes (native, expanded) |
| Multi-shot | yes (MM-RoPE) | yes | yes (frame-precise) |
| Max ref assets | text + image | text + image + audio | up to 12 mixed |
| Max duration | 5–10 s | up to 15 s | up to 15 s per shot |
| Distillation | TSCD ~4× | acceleration framework >10× | unknown |
| Public weights | no | no | no |
| Public technical report | yes | yes | **no** |
