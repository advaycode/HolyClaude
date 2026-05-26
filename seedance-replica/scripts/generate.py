"""
generate.py — CLI front-end for text-to-video and image-to-video generation.

Usage:
    python scripts/generate.py --preset balanced --prompt "..." --out out/clip.mp4

This script orchestrates the underlying backbone (Wan 2.2 / LTX) via the diffusers
API. For maximum performance use the ComfyUI workflows in configs/comfyui_workflows/.
"""

from __future__ import annotations

import argparse
import os
import sys
import time
from pathlib import Path
from typing import Optional

import torch
import yaml
from rich import print as rprint
from rich.console import Console
from rich.progress import (BarColumn, Progress, SpinnerColumn, TextColumn,
                           TimeElapsedColumn, TimeRemainingColumn)

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

CACHE_ROOT = Path(os.environ.get("SEEDANCE_CACHE", Path.home() / ".cache" / "seedance-replica"))
CONSOLE = Console()

# Rough per-step seconds on RTX 4070 12 GB. Used to give an upfront ETA *before*
# the diffusers progress bar appears. Updated empirically; conservative.
PER_STEP_SECONDS = {
    "fast":     {480: 1.2, 720: 2.5, 1080: 5.0},
    "balanced": {480: 2.5, 720: 5.5, 1080: 12.0},
    "quality":  {480: 7.0, 720: 16.0, 1080: 35.0},
}
DECODE_SECONDS = {"fast": 4, "balanced": 12, "quality": 25}
LOAD_SECONDS   = {"fast": 15, "balanced": 25, "quality": 45}


def estimate_runtime(preset: str, height: int, steps: int) -> dict:
    """Return {load, sample, decode, total} seconds estimate for upfront display."""
    # snap height to nearest known bucket
    buckets = sorted(PER_STEP_SECONDS[preset].keys())
    h = min(buckets, key=lambda b: abs(b - height))
    sample = PER_STEP_SECONDS[preset][h] * steps
    return {
        "load": LOAD_SECONDS[preset],
        "sample": sample,
        "decode": DECODE_SECONDS[preset],
        "total": LOAD_SECONDS[preset] + sample + DECODE_SECONDS[preset],
    }


def fmt_time(seconds: float) -> str:
    m, s = divmod(int(seconds), 60)
    return f"{m}m {s:02d}s" if m else f"{s}s"


def progress_callback(pipe, step, timestep, callback_kwargs):
    """diffusers callback_on_step_end hook — updates the rich bar from the global handle."""
    if hasattr(progress_callback, "task") and progress_callback.task is not None:
        progress_callback.bar.update(progress_callback.task, advance=1)
    return callback_kwargs


def load_config(preset: str) -> dict:
    cfg_path = ROOT / "configs" / f"4070_{preset}.yaml"
    if not cfg_path.exists():
        rprint(f"[red]config not found: {cfg_path}[/red]")
        sys.exit(1)
    return yaml.safe_load(cfg_path.read_text(encoding="utf-8"))


def expand_prompt(prompt: str, cfg: dict) -> str:
    """Optional Qwen2.5-based prompt expansion."""
    pe = cfg.get("prompt_expander", {})
    if not pe.get("enabled"):
        return prompt
    try:
        from llama_cpp import Llama
    except ImportError:
        rprint("[yellow]llama-cpp-python not installed; skipping prompt expansion[/yellow]")
        return prompt

    model_file = CACHE_ROOT / "models" / "qwen25_7b_gguf" / pe["model"]
    if not model_file.exists():
        rprint(f"[yellow]expander weights missing: {model_file}; skipping[/yellow]")
        return prompt

    llm = Llama(model_path=str(model_file), n_ctx=2048, n_gpu_layers=0)  # CPU; runs once per call
    sys_msg = pe["system_prompt"]
    out = llm.create_chat_completion(
        messages=[
            {"role": "system", "content": sys_msg},
            {"role": "user", "content": prompt},
        ],
        temperature=0.7,
        max_tokens=200,
    )
    expanded = out["choices"][0]["message"]["content"].strip()
    rprint(f"[dim]expanded:[/dim] {expanded}")
    return expanded


def run_balanced(args, cfg: dict) -> Path:
    """Wan 2.2 TI2V-5B via diffusers."""
    from diffusers import WanPipeline  # type: ignore[attr-defined]  # provided by diffusers >=0.31
    from PIL import Image

    model_dir = CACHE_ROOT / "models" / "wan22_5b"
    h, w = cfg["video"]["default_resolution"][1], cfg["video"]["default_resolution"][0]
    frames = args.duration * cfg["video"]["default_fps"] if args.duration else cfg["video"]["default_frames"]
    frames = max(1, min(frames, cfg["video"]["max_frames"]))
    steps = args.num_steps or cfg["sampling"]["num_steps"]

    eta = estimate_runtime("balanced", h, steps)
    CONSOLE.rule(f"[bold cyan]Balanced preset · {frames} frames @ {w}x{h} · {steps} steps")
    CONSOLE.print(f"[dim]Estimated wall time: ~{fmt_time(eta['total'])}  "
                  f"(load ~{fmt_time(eta['load'])}, sample ~{fmt_time(eta['sample'])}, "
                  f"decode ~{fmt_time(eta['decode'])})[/dim]")

    with Progress(SpinnerColumn(), TextColumn("[bold blue]{task.description}"),
                  TimeElapsedColumn(), console=CONSOLE, transient=True) as p:
        t = p.add_task("loading Wan 2.2 TI2V-5B...", total=None)
        pipe = WanPipeline.from_pretrained(str(model_dir), torch_dtype=torch.float16).to("cuda")
        if cfg["memory"].get("enable_sage_attention"):
            try:
                from sageattention import sageattn
                pipe.transformer.set_attn_processor(sageattn)
            except Exception: pass
        if cfg["memory"].get("blocks_to_swap", 0) > 0:
            try: pipe.transformer.enable_cpu_offload(blocks_to_swap=cfg["memory"]["blocks_to_swap"])
            except Exception: pipe.enable_sequential_cpu_offload()
        if cfg["memory"].get("vae_decode_mode") == "tiled":
            pipe.vae.enable_tiling()
        p.update(t, description="model ready")

    init_image = Image.open(args.image).convert("RGB") if args.image else None
    gen = torch.Generator(device="cuda").manual_seed(args.seed)

    t0 = time.time()
    with Progress(
        TextColumn("[bold green]sampling[/bold green]"),
        BarColumn(),
        TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
        TextColumn("step {task.completed}/{task.total}"),
        TimeElapsedColumn(),
        TextColumn("eta"),
        TimeRemainingColumn(),
        console=CONSOLE,
    ) as p:
        sample_task = p.add_task("sampling", total=steps)
        progress_callback.bar = p
        progress_callback.task = sample_task
        out = pipe(
            prompt=args.prompt,
            negative_prompt=args.negative,
            image=init_image,
            height=h, width=w,
            num_frames=frames,
            num_inference_steps=steps,
            guidance_scale=args.cfg or cfg["sampling"]["cfg_scale"],
            generator=gen,
            callback_on_step_end=progress_callback,
        )
        progress_callback.task = None

    with Progress(SpinnerColumn(), TextColumn("[bold blue]decoding VAE → frames..."),
                  TimeElapsedColumn(), console=CONSOLE, transient=True) as p:
        p.add_task("decode", total=None)
        # diffusers already decoded inside the pipe call; this block is symbolic.
        # If you switch to manual VAE decode, put pipe.vae.decode() here.

    elapsed = time.time() - t0
    CONSOLE.print(f"[bold green]✓ done in {fmt_time(elapsed)}[/bold green]  "
                  f"[dim](estimate was {fmt_time(eta['total'])})[/dim]")

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    _save_video(out.frames[0], out_path, fps=args.fps or cfg["video"]["default_fps"])
    return out_path


def run_fast(args, cfg: dict) -> Path:
    """LTX-Video 0.9.8 distilled via diffusers."""
    from diffusers import LTXPipeline  # type: ignore[attr-defined]
    model_dir = CACHE_ROOT / "models" / "ltx"
    w, h = cfg["video"]["default_resolution"]
    frames = args.duration * cfg["video"]["default_fps"] if args.duration else 97
    steps = args.num_steps or cfg["sampling"]["num_steps"]

    eta = estimate_runtime("fast", h, steps)
    CONSOLE.rule(f"[bold cyan]Fast preset (LTX) · {frames} frames @ {w}x{h} · {steps} steps")
    CONSOLE.print(f"[dim]Estimated wall time: ~{fmt_time(eta['total'])}[/dim]")

    with Progress(SpinnerColumn(), TextColumn("[bold blue]{task.description}"),
                  TimeElapsedColumn(), console=CONSOLE, transient=True) as p:
        p.add_task("loading LTX-Video 0.9.8 distilled...", total=None)
        pipe = LTXPipeline.from_pretrained(str(model_dir), torch_dtype=torch.float16).to("cuda")
        if cfg["memory"].get("vae_decode_mode") == "tiled":
            pipe.vae.enable_tiling()

    gen = torch.Generator(device="cuda").manual_seed(args.seed)
    t0 = time.time()
    with Progress(
        TextColumn("[bold green]sampling[/bold green]"),
        BarColumn(),
        TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
        TextColumn("step {task.completed}/{task.total}"),
        TimeElapsedColumn(),
        TextColumn("eta"),
        TimeRemainingColumn(),
        console=CONSOLE,
    ) as p:
        sample_task = p.add_task("sampling", total=steps)
        progress_callback.bar = p
        progress_callback.task = sample_task
        out = pipe(
            prompt=args.prompt,
            negative_prompt=args.negative,
            height=h, width=w,
            num_frames=frames,
            num_inference_steps=steps,
            guidance_scale=args.cfg or cfg["sampling"]["cfg_scale"],
            generator=gen,
            callback_on_step_end=progress_callback,
        )
        progress_callback.task = None

    elapsed = time.time() - t0
    CONSOLE.print(f"[bold green]✓ done in {fmt_time(elapsed)}[/bold green]  "
                  f"[dim](estimate was {fmt_time(eta['total'])})[/dim]")

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    _save_video(out.frames[0], out_path, fps=args.fps or cfg["video"]["default_fps"])
    return out_path


def run_quality(args, cfg: dict) -> Path:
    """Wan 2.2 14B GGUF via ComfyUI API.

    GGUF inference is much smoother through the ComfyUI graph (custom GGUF loader,
    MoE switching node). This function shells out to ComfyUI via its websocket API.
    """
    from scripts._comfyui_client import run_quality_workflow  # local helper
    rprint("[cyan]Quality preset uses ComfyUI backend (GGUF MoE).[/cyan]")
    rprint("[dim]starting ComfyUI on :8188 if not running...[/dim]")
    return run_quality_workflow(args, cfg)


def _save_video(frames, out_path: Path, fps: int):
    """frames: list[PIL.Image] or numpy array. Write MP4 via imageio."""
    import imageio
    import numpy as np
    arr = [np.asarray(f) for f in frames]
    imageio.mimsave(str(out_path), arr, fps=fps, codec="libx264", quality=8)
    rprint(f"[green]wrote {out_path}[/green]")


def main():
    p = argparse.ArgumentParser(description="Seedance-Replica video generator")
    p.add_argument("--preset", choices=["fast", "balanced", "quality"], default="balanced")
    p.add_argument("--prompt", required=True)
    p.add_argument("--negative", default="blurry, low quality, distorted, warped, choppy motion, watermark, text, extra limbs, deformed hands, jpeg artifacts")
    p.add_argument("--image", type=Path, help="optional first-frame image for I2V")
    p.add_argument("--lora", type=Path, action="append", help="LoRA file (repeatable)")
    p.add_argument("--lora-weight", type=float, default=0.8)
    p.add_argument("--duration", type=int, default=5, help="seconds")
    p.add_argument("--fps", type=int, help="output fps")
    p.add_argument("--resolution", help="e.g. 720p, 480p, 1280x720")
    p.add_argument("--seed", type=int, default=42)
    p.add_argument("--num-steps", type=int, help="override config")
    p.add_argument("--cfg", type=float, help="override config")
    p.add_argument("--prompt-expander", help="qwen2.5-7b to enable expansion")
    p.add_argument("--show-expanded", action="store_true")
    p.add_argument("--out", type=Path, required=True)
    args = p.parse_args()

    cfg = load_config(args.preset)

    if args.resolution:
        if args.resolution.endswith("p"):
            heights = {"480p": [854, 480], "720p": [1280, 720], "1080p": [1920, 1080]}
            cfg["video"]["default_resolution"] = heights.get(args.resolution, cfg["video"]["default_resolution"])
        elif "x" in args.resolution:
            w, h = (int(x) for x in args.resolution.lower().split("x"))
            cfg["video"]["default_resolution"] = [w, h]

    if args.prompt_expander:
        cfg.setdefault("prompt_expander", {})["enabled"] = True
        args.prompt = expand_prompt(args.prompt, cfg)

    runner = {"fast": run_fast, "balanced": run_balanced, "quality": run_quality}[args.preset]
    runner(args, cfg)


if __name__ == "__main__":
    main()
