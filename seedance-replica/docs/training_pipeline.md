# Training Pipeline

How to fine-tune the open base on your own data so the output starts to look like your version of Seedance.

You will **not pretrain**. You will **LoRA-finetune** a published Wan 2.2 checkpoint. Optionally you'll distill to 4-step inference.

---

## Pipeline overview

```
your video clips (mp4/mov)
         │
   ┌─────▼──────┐
   │  trim &    │  ffmpeg, 5–15 s clips, 720p
   │  pre-proc  │
   └─────┬──────┘
         │
   ┌─────▼──────────────┐
   │ caption_video.py   │  ShareCaptioner-Video → dense captions
   └─────┬──────────────┘
         │
   ┌─────▼──────────────┐
   │ build webdataset    │  tar shards for musubi-tuner
   └─────┬──────────────┘
         │
   ┌─────▼──────────────┐
   │  train_lora.py      │  rank-32 LoRA, fp8 + blocks-swap, ~6 h
   └─────┬──────────────┘
         │
   ┌─────▼──────────────┐
   │ test + iterate      │  generate samples, eyeball, retrain
   └─────┬──────────────┘
         │
   ┌─────▼──────────────────┐
   │ distill_causvid.py     │  optional, 4-step LoRA for fast inference
   └─────┬──────────────────┘
         │
   ┌─────▼──────────────┐
   │  serve via          │  generate.py / ComfyUI
   │  generate.py        │
   └─────────────────────┘
```

---

## Stage 1 — Data collection

**What you want**: 30–500 short video clips that all share the *thing* you want to learn. Style, character, motion, world, anything consistent.

- Source: YouTube, Pexels, your own footage, public domain archives
- Format: MP4 H.264, 24 or 30 fps
- Duration: 5–15 s each (longer wastes compute)
- Resolution: at least 720p; downscale higher if needed
- Variety: avoid all-static, all-talking-head, all-same-subject — train data should span the *intended distribution*

**Trim with ffmpeg**:
```powershell
ffmpeg -i input.mp4 -ss 00:00:10 -t 8 -vf scale=1280:720 -r 24 -c:v libx264 -crf 18 -an out_0001.mp4
```

Drop everything into `data/my_clips/`.

---

## Stage 2 — Captioning

Run **ShareCaptioner-Video** over your corpus. Outputs dense captions describing what's happening, camera, lighting, characters.

```powershell
python scripts/caption_video.py \
  --input data/my_clips/ \
  --output data/my_clips_captions.json \
  --captioner share-captioner-video \
  --max-length 120 \
  --include-camera \
  --include-lighting
```

First run downloads the captioner (~7 GB). Subsequent runs are cached.

Speed: ~30–60 s per clip on a 4070 (the captioner is fp16, runs in ~5 GB).

**Caption format** (what Wan 2.2 expects after our wrapper):
```json
{
  "clip_0001.mp4": "A young woman with long dark hair walks down a rain-slick Tokyo street at night, neon signs reflecting in puddles. The camera slowly pushes in from a wide shot to a medium shot. Soft cyan and magenta key light, shallow depth of field, cinematic 35 mm look.",
  ...
}
```

**Review the captions.** Bad captions kill LoRA quality. Spend an hour fixing the worst 10%.

---

## Stage 3 — Webdataset packing

Musubi-tuner ingests webdataset tar shards. Our helper script:

```powershell
python scripts/build_webdataset.py \
  --videos data/my_clips/ \
  --captions data/my_clips_captions.json \
  --output data/my_clips_wds/ \
  --shard-size 1000
```

Output: `data/my_clips_wds/shard_{0000..0009}.tar`.

---

## Stage 4 — LoRA training

```powershell
python scripts/train_lora.py \
  --data data/my_clips_wds/ \
  --base wan2.2-ti2v-5b \
  --rank 32 \
  --alpha 32 \
  --steps 4000 \
  --lr 1e-4 \
  --warmup 200 \
  --scheduler cosine \
  --batch-size 1 \
  --grad-accum 4 \
  --resolution 720 \
  --num-frames 81 \
  --fp8 \
  --blocks-to-swap 20 \
  --save-every 1000 \
  --output loras/my_style_v1.safetensors
```

What the flags do:
- `--rank 32` → LoRA rank, controls capacity vs file size (~150 MB at rank 32)
- `--alpha 32` → scaling, keep equal to rank
- `--steps 4000` → enough for a clear style; 8000 for more bake
- `--lr 1e-4` → safe; lower if you see instability
- `--batch-size 1 --grad-accum 4` → effective batch 4 with 12 GB
- `--num-frames 81` → 81 frames @ 24 fps = ~3.4 s clips during training; Wan's native window
- `--fp8` → fp8 weight casting, halves VRAM
- `--blocks-to-swap 20` → offload 20 transformer blocks to CPU RAM each step

VRAM target: 10–11 GB. If you OOM, raise `--blocks-to-swap` to 30 or drop `--num-frames` to 49.

Throughput on 4070: ~1.0–1.5 sec/step. 4000 steps = 70–100 min wall time per epoch.

**Watch the loss in TensorBoard** (`tensorboard --logdir runs/`). You want:
- Loss curve declining smoothly, plateau around step 2000–3000
- Sample generations every 1000 steps showing increasing style adherence
- No instability spikes (those mean LR too high)

---

## Stage 5 — Test & iterate

After step 1000, 2000, 3000, 4000 you get a checkpoint. Try each:

```powershell
foreach ($ckpt in @(1000, 2000, 3000, 4000)) {
  python scripts/generate.py `
    --preset balanced `
    --lora loras/my_style_v1_step_$ckpt.safetensors `
    --lora-weight 0.8 `
    --prompt "test prompt that exercises the style" `
    --seed 42 `
    --out out/test_step_$ckpt.mp4
}
```

Pick the checkpoint where style is strong but prompt adherence hasn't crumbled. That's usually step 2000–3000.

LoRA weight at inference:
- `0.5–0.7` → subtle style hint
- `0.8–1.0` → strong style
- `>1.0` → overcooked, breaks structure

---

## Stage 6 — Distill (optional, advanced)

If your LoRA is good and you want sub-30-second generation:

```powershell
python scripts/distill_causvid.py \
  --teacher loras/my_style_v1.safetensors \
  --base wan2.2-ti2v-5b \
  --steps 8000 \
  --student-steps 4 \
  --output loras/my_style_v1_causvid_4step.safetensors
```

This trains a separate LoRA that, when applied, lets Wan generate in 4 steps instead of 30 with minimal quality loss.

Wall time: 12–24 h on 4070. Output: a `~150 MB` LoRA you apply at inference with `--num-steps 4`.

---

## Stage 7 — Serve

Two options:

**CLI** (this repo):
```powershell
python scripts/generate.py --preset balanced --lora loras/my_style_v1.safetensors --prompt "..."
```

**ComfyUI** (drop the LoRA into `ComfyUI/models/loras/` and load via the LoRA node in the workflow in `configs/comfyui_workflows/`).

---

## What you skip vs. ByteDance's pipeline

| Their stage | We do | We skip |
|---|---|---|
| Image pretrain (256 px) | — | ✓ (use pretrained Wan) |
| Video pretrain | — | ✓ |
| Joint T2V+I2V SFT | — | ✓ |
| Multi-shot fine-tuning | partial via prompt scaffolding | mostly ✓ |
| RLHF (3 reward models) | manual SFT preference selection | mostly ✓ |
| Inference distillation | CausVid | — |
| Multi-modal joint A+V training | — | ✓ (we use MMAudio) |
| Multi-lingual coverage | — | ✓ (Wan native multilingual via UMT5) |

We hit ~5% of their compute. The pretrained Wan base does the heavy lifting.

---

## Storage budget

| Item | Size |
|---|---|
| Wan 2.2 TI2V-5B base | ~10 GB |
| Wan 2.2 14B GGUF Q5 | ~6 GB |
| UMT5-XXL | ~9 GB |
| Wan 2.2 VAE | ~250 MB |
| LTX-Video 13B distilled | ~13 GB |
| MMAudio | ~3 GB |
| ShareCaptioner-Video | ~7 GB |
| LatentSync | ~3 GB |
| Real-ESRGAN, RIFE | ~200 MB |
| Per LoRA you train | ~150 MB |
| Training data (200 clips × 720p × 8 s) | ~10–20 GB |
| Webdataset shards | ~10 GB |
| **Total cold install** | **~75 GB** |
| **Recommended SSD free** | **200 GB** |
