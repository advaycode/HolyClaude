"""
download_models.py — pull all weights for a chosen preset to the cache dir.

Usage:
    python scripts/download_models.py --preset balanced
    python scripts/download_models.py --preset all
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

from huggingface_hub import snapshot_download
from rich import print as rprint
from rich.progress import Progress

CACHE_ROOT = Path(os.environ.get("SEEDANCE_CACHE", Path.home() / ".cache" / "seedance-replica"))

# (repo_id, files | None, local_subdir, gated)  ── None means full snapshot
DOWNLOADS = {
    "fast": [
        ("Lightricks/LTX-Video-0.9.8-13B-distilled", None, "models/ltx", False),
    ],
    "balanced": [
        ("Wan-AI/Wan2.2-TI2V-5B-Diffusers", None, "models/wan22_5b", False),
    ],
    "quality": [
        ("QuantStack/Wan2.2-T2V-A14B-GGUF",
         ["Wan2_2-T2V-A14B-HighNoise-Q5_K_M.gguf",
          "Wan2_2-T2V-A14B-LowNoise-Q5_K_M.gguf"],
         "models/wan22_14b_gguf", False),
        ("Wan-AI/Wan2.2-TI2V-5B-Diffusers", ["vae/Wan2_2_VAE.safetensors"],
         "models/wan22_14b_gguf/vae", False),
        ("google/umt5-xxl", None, "models/umt5_xxl", False),
        # Optional prompt expander
        ("bartowski/Qwen2.5-7B-Instruct-GGUF",
         ["Qwen2.5-7B-Instruct-Q4_K_M.gguf"],
         "models/qwen25_7b_gguf", False),
    ],
    "audio": [
        ("hkchengrex/MMAudio", None, "models/mmaudio", False),
    ],
    "captioner": [
        ("Lin-Chen/ShareCaptioner-Video", None, "models/share_captioner_video", False),
    ],
    "upscale": [
        ("ai-forever/Real-ESRGAN", None, "models/realesrgan", False),
    ],
    "lipsync": [
        ("ByteDance/LatentSync", None, "models/latentsync", True),  # gated
    ],
}


def download_set(name: str, items, cache: Path):
    rprint(f"\n[bold cyan]== {name} ==[/bold cyan]")
    cache.mkdir(parents=True, exist_ok=True)
    with Progress() as bar:
        task = bar.add_task(f"[{name}]", total=len(items))
        for repo, files, subdir, gated in items:
            local = cache / subdir
            local.mkdir(parents=True, exist_ok=True)
            try:
                snapshot_download(
                    repo_id=repo,
                    local_dir=str(local),
                    allow_patterns=files,
                    local_dir_use_symlinks=False,
                )
                rprint(f"  [green]ok[/green] {repo}")
            except Exception as e:
                if gated:
                    rprint(f"  [yellow]gated[/yellow] {repo} — accept license at https://huggingface.co/{repo}")
                else:
                    rprint(f"  [red]fail[/red] {repo}: {e}")
            bar.advance(task)


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--preset", choices=["fast", "balanced", "quality", "audio", "captioner",
                                        "upscale", "lipsync", "all"], default="balanced")
    p.add_argument("--cache-dir", type=Path, default=CACHE_ROOT)
    args = p.parse_args()

    cache = args.cache_dir
    rprint(f"[dim]cache: {cache}[/dim]")

    if args.preset == "all":
        order = ["fast", "balanced", "quality", "audio", "captioner", "upscale", "lipsync"]
    else:
        # Most presets need audio + upscale alongside
        order = [args.preset]
        if args.preset in ("balanced", "quality"):
            order += ["audio", "upscale"]

    for name in order:
        download_set(name, DOWNLOADS[name], cache)

    rprint("\n[bold green]Download complete.[/bold green]")
    rprint(f"Cache size: see [dim]du -sh {cache}[/dim]")


if __name__ == "__main__":
    main()
