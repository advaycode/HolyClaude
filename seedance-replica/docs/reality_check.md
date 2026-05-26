# Reality Check — H100 Cluster vs RTX 4070

## TL;DR

ByteDance trains Seedance on something like **1,000–10,000 H100/H800 GPUs** for **weeks**. The RTX 4070 has **~1/40th the compute of an H100 and 1/8th the memory**. Multiply: training Seedance from scratch on a single 4070 would take roughly **10,000–100,000 years**. Not figurative.

What we *can* do is **inherit a pretrained open base model** (Wan 2.2, LTX, Hunyuan) and:
- Fine-tune with LoRA (~6 h)
- Distill with CausVid (~12 h)
- Serve at consumer speeds (~30 s – 8 min per clip)

That's the actual scope. Anyone who tells you they have a "from-scratch Seedance replica on a single GPU" is lying.

---

## Hardware gap, numbers

| Spec | H100 SXM | RTX 4070 | Ratio |
|---|---|---|---|
| FP16 TFLOPs (no sparsity) | 989 | ~29 (TF32 base, fp16 with TC) | ~34× |
| FP8 TFLOPs (E4M3, no sparsity) | 1,979 | ~58 | ~34× |
| HBM / VRAM | 80 GB HBM3 | 12 GB GDDR6X | 6.7× |
| Memory bandwidth | 3.35 TB/s | 504 GB/s | 6.6× |
| NVLink/inter-GPU bw | 900 GB/s | n/a (PCIe 4 ×16: 32 GB/s) | 28× |

A typical pretraining run for a 10 B+ video DiT uses **all of the above at once**, for **weeks**. ByteDance has published they used hybrid parallelism (data + tensor + pipeline) — that's not possible with one GPU.

---

## What pretraining actually costs

Public estimates for similar-scale video models:

| Model | Reported / inferred GPU-hours | $ at $2/h spot |
|---|---|---|
| Sora (estimate) | ~10,000,000 H100-h | ~$20 M |
| Wan 2.1 14B (public) | ~3,000,000 A100-h equiv | ~$6 M |
| HunyuanVideo (public) | ~2,000,000 H800-h equiv | ~$4 M |
| Seedance 1.0 (inferred) | ~5,000,000 H100-h | ~$10 M |
| Seedance 1.5 Pro / 2.0 | unknown, likely 2–4× above | $20–40 M+ |

A single 4070 at 100% utilization for a year = 8,760 GPU-h. To match Seedance 1.0's pretraining you'd need **~570 years of 4070 runtime**. (And the 4070 is ~25× slower than H100 per-clock for the relevant ops, so multiply again.)

---

## What you CAN do on a 4070

### Strong: inference

Wan 2.2 14B GGUF Q5 on RTX 4070 generates 5 s 720p video in ~3 minutes. That's 95% of what people use Seedance for in practice.

### Strong: LoRA finetuning

musubi-tuner enables rank-16 to rank-64 LoRA training on Wan 2.2 5B in 12 GB. ~6 h for a solid style LoRA on 30–100 clips.

### Medium: full-rank finetuning of small models

The Wan 2.2 5B base can be full-finetuned at low res with aggressive offloading. Not recommended unless you have weeks.

### Medium: distillation

CausVid-style distillation of your LoRA'd model to 4 steps is feasible in 8–24 h on a single 4070. The student is smaller and faster than the teacher; you skip the bidirectional teacher's full forward by using the original Wan as teacher.

### Weak: anything that needs >12 GB activations

Long videos (>10 s), 1080p native diffusion, or full-rank training of 14 B models all need either model parallelism (you don't have it) or massive offloading (slow).

### Impossible: pretraining from scratch

Don't even try.

---

## Quality ceiling honestly

If you do everything in this repo perfectly, where does the output land?

| Quality dimension | Seedance 2.0 (Elo) | This repo, honest estimate |
|---|---|---|
| Prompt adherence | 95th percentile | 70th–80th |
| Motion stability | 95th | 75th |
| Aesthetic / composition | 95th | 70th (depends on your LoRA) |
| Multi-shot consistency | 90th | 50th–65th |
| Audio sync | 90th (native) | 70th (post-hoc) |
| Lip-sync | 85th | 75th (with LatentSync) |
| Long-form (>30 s) | 85th | 45th |

That's roughly **late-2024 / early-2025 commercial-grade output** delivered locally and free.

If you need top-tier quality for a paying client, **use the Higgsfield Seedance 2.0 API** at $0.25–$0.50/sec and pocket the difference. If you need privacy, control, dataset sovereignty, or zero marginal cost — this repo.

---

## What this repo deliberately *does not* try to do

1. **Pretrain from scratch.** Infeasible on consumer hardware.
2. **Bit-for-bit reproduce Seedance weights.** They aren't open.
3. **Match Seedance API throughput.** Seedance is served on H100/H800; we're on 4070.
4. **Reverse-engineer the joint audio-video VAE.** Use MMAudio as a separate stage.
5. **Train novel architectures.** Stand on shoulders of Wan, LTX, Hunyuan, MMAudio.

It DOES try to:

1. Give the friend with a 4070 a **single repo to clone** and a **single command to generate**.
2. Match Seedance ergonomics (prompt → video, optional image, optional audio).
3. Provide a finetuning path so the output can be customized to a specific style.
4. Provide an audio path that sounds intentional, not slapped-on.
5. Be honest about every limitation.
