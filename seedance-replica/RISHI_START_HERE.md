# Hey Rishi — Start Here

This is a Seedance-2.0-style video generator for your RTX 4070. You'll go from `git clone` to a working AI-generated video in about **90 minutes** (most of that is downloading model weights — go play a game).

Built by Advay. If anything below breaks, ping him with the exact error message.

---

## What you'll be running

A local video generation stack built on **Wan 2.2** (the closest open-source equivalent to ByteDance's Seedance). It generates 720p video clips up to 5 seconds from text prompts. With finetuning it can match a specific style — anime, cinematic, your own footage, whatever.

**It won't be identical to Higgsfield Seedance 2.0** — that runs on multi-thousand-dollar enterprise GPUs. But it'll be in the same league as Seedance 1.0, fully local, and free forever once it's installed.

---

## Before you start — check these

Open PowerShell and run:

```powershell
nvidia-smi
```

You need:
- **NVIDIA driver version 555 or newer** (top row of nvidia-smi)
- **RTX 4070 with 12 GB VRAM** confirmed
- **At least 200 GB free** on whichever drive you'll install to
- **32 GB system RAM strongly recommended** (16 GB will work but slow)

If your driver is older than 555, update from [nvidia.com/drivers](https://www.nvidia.com/Download/index.aspx) first.

---

## Step 1 — Clone the repo (1 minute)

```powershell
cd C:\
git clone -b seedance-replica https://github.com/advaycode/HolyClaude.git
cd HolyClaude\seedance-replica
```

If `git` isn't installed: install it from [git-scm.com](https://git-scm.com/download/win) first.

---

## Step 2 — Run the installer (~15 minutes)

Right-click PowerShell → **Run as Administrator**, then:

```powershell
cd C:\HolyClaude\seedance-replica
Set-ExecutionPolicy -Scope Process Bypass -Force
.\scripts\install_4070.ps1
```

What this does:
- Installs Python 3.11, ffmpeg, 7zip if you don't have them
- Creates a Python virtual environment (`.venv\`)
- Installs PyTorch with CUDA 12.4 (~3 GB download)
- Installs ComfyUI + custom nodes to `C:\Users\<you>\ComfyUI\`
- Installs MMAudio, musubi-tuner, and other dependencies

**Expected**: a long stream of `pip install` output ending in `== Install complete ==`.

**If it fails on `sageattention`**: that's fine, the script continues without it. You'll just be ~30% slower at generation.

**If it fails on something else**: send Advay the last 20 lines.

---

## Step 3 — Download the model weights (~25 minutes, 22 GB)

This step needs the virtual environment active. Run:

```powershell
cd C:\HolyClaude\seedance-replica
.venv\Scripts\Activate.ps1
python scripts\download_models.py --preset balanced
```

This pulls down:
- Wan 2.2 TI2V-5B (~10 GB)
- MMAudio audio model (~3 GB)
- Real-ESRGAN upscaler (~200 MB)
- A few other support files (~8 GB)

**Expected**: progress bars from Hugging Face. Coffee break.

By default it caches to `C:\Users\<you>\.cache\seedance-replica\`. If your C: drive is full, override with `--cache-dir D:\models\seedance`.

---

## Step 4 — Generate your first video (~3 minutes)

This is the moment of truth.

```powershell
python scripts\generate.py `
  --preset balanced `
  --prompt "a samurai walks through cherry blossoms at dusk, cinematic, slow dolly forward" `
  --duration 5 `
  --seed 42 `
  --out out\first_clip.mp4
```

**What you'll see** (in order):
1. A header: `──── Balanced preset · 121 frames @ 1280x720 · 30 steps ────`
2. An upfront estimate: `Estimated wall time: ~3m 30s  (load ~25s, sample ~2m 45s, decode ~12s)`
3. A spinner while the model loads (~30 seconds)
4. A live progress bar through the 30 sampling steps:
   ```
   sampling ████████░░░░░░░░░░  47%  step 14/30  0:01:18  eta 0:01:32
   ```
   It shows percentage, current step, elapsed time, and **live ETA that updates each step**. The ETA gets accurate after the first 2–3 steps once it knows your real per-step speed.
5. A "decoding VAE → frames…" spinner (~10 seconds)
6. `✓ done in 3m 18s  (estimate was 3m 30s)` — actual vs. estimate
7. `wrote out/first_clip.mp4`

**Open `out\first_clip.mp4`** — you should see a samurai walking through cherry blossoms. Quality won't be perfect on first try; that's normal.

**While it's running, open a second PowerShell and run `nvidia-smi -l 1`** to watch VRAM. It should peak around 10–11 GB. If it hits 12 GB and crashes (Out Of Memory), see "If you OOM" below.

---

## Step 5 — Add audio (~30 seconds)

```powershell
python scripts\add_audio.py `
  --video out\first_clip.mp4 `
  --prompt "soft wind through trees, distant temple bell, ambient pads" `
  --out out\first_clip_with_audio.mp4
```

This runs MMAudio over your clip and produces synced ambient audio. Open `out\first_clip_with_audio.mp4` and you should hear wind + a faint bell, timed to the video.

---

## You did it 🎉

Try these prompts next:

```powershell
# cinematic
python scripts\generate.py --preset balanced --seed 7 --out out\rooftop.mp4 `
  --prompt "a hooded figure stands on a rooftop overlooking neon-soaked Tokyo at night, rain falling, slow push in, anamorphic"

# nature
python scripts\generate.py --preset balanced --seed 11 --out out\leopard.mp4 `
  --prompt "a snow leopard crosses a high ridge against a vast snowfield, telephoto, soft overcast light, slow motion"

# stylized
python scripts\generate.py --preset balanced --seed 23 --out out\crane.mp4 `
  --prompt "a red origami crane unfolds into a real bird mid-flight over a sunset lake, Hayao Miyazaki palette, tracking shot"

# portrait (try this with your own selfie as the first frame)
python scripts\generate.py --preset balanced --seed 42 --out out\portrait.mp4 `
  --image C:\path\to\your\photo.jpg `
  --prompt "the subject slowly turns and smiles, soft window light"
```

Better-prompt cheatsheet is in `data\prompts\seedance_style.md`.

---

## When things break

| Symptom | Fix |
|---|---|
| **CUDA out of memory** | Add `--resolution 480p`. If still OOM, add `--blocks-to-swap 30` to offload more to RAM. |
| **Black/green frames** | Restart the script — usually a CUDA quirk. If persistent, add `--num-steps 25`. |
| **`ModuleNotFoundError`** | Make sure `.venv\Scripts\Activate.ps1` ran. You should see `(.venv)` in your prompt. |
| **Generation takes 20+ min** | You're probably on the `quality` preset. Switch to `balanced`. Quality is meant for hero shots, not iteration. |
| **`torch.cuda.is_available()` returns False** | Driver too old or PyTorch installed wrong CUDA. Re-run `install_4070.ps1 -Force`. |
| **HuggingFace 401 errors** | The lipsync model is gated; either skip lipsync or accept the license at https://huggingface.co/ByteDance/LatentSync and re-run. |
| **It generates but looks bad** | Try a different seed (just change `--seed 42` to any number). Same prompt, different seed → very different output. Try 4–5 seeds before judging the prompt. |

---

## Wanna get fancy?

Once the basics work, try:

- **Three-shot sequence**: `python scripts\multishot.py --shots data\prompts\example_sequence.json --out out\seq.mp4`
- **Train a LoRA on your own footage**: drop 30+ clips into `data\my_clips\`, then follow `docs\training_pipeline.md`
- **Use ComfyUI's visual editor**: launch `python C:\Users\<you>\ComfyUI\main.py --listen 127.0.0.1 --port 8188`, open `http://localhost:8188` in your browser, load workflows from `configs\comfyui_workflows\`

---

## Honest expectations

What you have now:
- **Seedance 1.0-era quality** — late-2024 commercial video AI, running on your machine
- **Free per-generation** (electricity only)
- **Fully private** — no prompts leave your machine
- **Customizable** — finetune on any style you can collect data for

What you don't have:
- **Seedance 2.0 quality** — that runs on $40k enterprise GPUs and they don't open-source the weights
- **Real-time generation** — closest is the `fast` preset (~30 sec for 4-sec clips, lower quality)
- **Native 4K / 60fps / 5-minute clips** — you can upscale and frame-interpolate to fake those, but native is gated by VRAM
- **Perfect lip-sync for talking heads** — close, but visible cracks in close-ups (LatentSync second pass helps)

If you need top-tier quality for a specific paying gig, just use Higgsfield's Seedance 2.0 API at ~$0.25/sec and call it done.

For everything else — experimenting, making style LoRAs, learning how this stack works, generating private content, running offline — this repo gets you there.

---

## More docs (when you're curious)

- `README.md` — full feature overview
- `ARCHITECTURE.md` — exactly what's under the hood and how each piece maps to Seedance
- `docs\reality_check.md` — honest H100-vs-4070 capability gap
- `docs\inference_pipeline.md` — every CLI flag explained
- `docs\training_pipeline.md` — LoRA training walkthrough
- `docs\audio_pipeline.md` — MMAudio + lip-sync details

Have fun. Send Advay screenshots when you make something cool.
