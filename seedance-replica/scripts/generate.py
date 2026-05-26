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

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

CACHE_ROOT = Path(os.environ.get("SEEDANCE_CACHE", Path.home() / ".cache" / "seedance-replica"))


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
    import numpy as np
    from PIL import Image

    model_dir = CACHE_ROOT / "models" / "wan22_5b"
    rprint(f"[dim]loading Wan 2.2 TI2V-5B from {model_dir}[/dim]")
    pipe = WanPipeline.from_pretrained(str(model_dir), torch_dtype=torch.float16).to("cuda")

    if cfg["memory"].get("enable_sage_attention"):
        try:
            from sageattention import sageattn
            pipe.transformer.set_attn_processor(sageattn)
        except Exception:
            pass

    if cfg["memory"].get("blocks_to_swap", 0) > 0:
        try:
            pipe.transformer.enable_cpu_offload(blocks_to_swap=cfg["memory"]["blocks_to_swap"])
        except Exception:
            pipe.enable_sequential_cpu_offload()

    if cfg["memory"].get("vae_decode_mode") == "tiled":
        pipe.vae.enable_tiling()

    init_image = None
    if args.image:
        init_image = Image.open(args.image).convert("RGB")

    gen = torch.Generator(device="cuda").manual_seed(args.seed)
    h, w = cfg["video"]["default_resolution"][1], cfg["video"]["default_resolution"][0]
    frames = args.duration * cfg["video"]["default_fps"] if args.duration else cfg["video"]["default_frames"]
    frames = max(1, min(frames, cfg["video"]["max_frames"]))

    rprint(f"[cyan]generating {frames} frames @ {w}x{h}, {cfg['sampling']['num_steps']} steps[/cyan]")
    t0 = time.time()
    out = pipe(
        prompt=args.prompt,
        negative_prompt=args.negative,
        image=init_image,
        height=h, width=w,
        num_frames=frames,
        num_inference_steps=args.num_steps or cfg["sampling"]["num_steps"],
        guidance_scale=args.cfg or cfg["sampling"]["cfg_scale"],
        generator=gen,
    )
    elapsed = time.time() - t0
    rprint(f"[green]done in {elapsed:.1f}s[/green]")

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    _save_video(out.frames[0], out_path, fps=args.fps or cfg["video"]["default_fps"])
    return out_path


def run_fast(args, cfg: dict) -> Path:
    """LTX-Video 0.9.8 distilled via diffusers."""
    from diffusers import LTXPipeline  # type: ignore[attr-defined]
    model_dir = CACHE_ROOT / "models" / "ltx"
    rprint(f"[dim]loading LTX-Video 0.9.8 distilled from {model_dir}[/dim]")
    pipe = LTXPipeline.from_pretrained(str(model_dir), torch_dtype=torch.float16).to("cuda")
    if cfg["memory"].get("vae_decode_mode") == "tiled":
        pipe.vae.enable_tiling()

    w, h = cfg["video"]["default_resolution"]
    frames = args.duration * cfg["video"]["default_fps"] if args.duration else 97
    gen = torch.Generator(device="cuda").manual_seed(args.seed)

    rprint(f"[cyan]LTX: {frames} frames @ {w}x{h}, {cfg['sampling']['num_steps']} steps[/cyan]")
    t0 = time.time()
    out = pipe(
        prompt=args.prompt,
        negative_prompt=args.negative,
        height=h, width=w,
        num_frames=frames,
        num_inference_steps=args.num_steps or cfg["sampling"]["num_steps"],
        guidance_scale=args.cfg or cfg["sampling"]["cfg_scale"],
        generator=gen,
    )
    rprint(f"[green]done in {time.time()-t0:.1f}s[/green]")

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
