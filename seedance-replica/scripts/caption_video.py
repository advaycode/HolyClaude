"""
caption_video.py — dense captions over a directory of clips.

Uses ShareCaptioner-Video (default) or AuroraCap. Outputs a JSON mapping
clip_filename → caption suitable for musubi-tuner training.

Usage:
    python scripts/caption_video.py --input data/my_clips/ --output data/my_clips_captions.json
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Optional

import torch
from rich import print as rprint
from rich.progress import track

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
CACHE_ROOT = Path(os.environ.get("SEEDANCE_CACHE", Path.home() / ".cache" / "seedance-replica"))


def load_share_captioner_video():
    """Loads the ShareCaptioner-Video model from cache."""
    from transformers import AutoModelForCausalLM, AutoTokenizer
    model_dir = CACHE_ROOT / "models" / "share_captioner_video"
    if not model_dir.exists():
        rprint(f"[red]captioner missing at {model_dir}. Run: python scripts/download_models.py --preset captioner[/red]")
        sys.exit(1)
    tok = AutoTokenizer.from_pretrained(str(model_dir), trust_remote_code=True)
    mdl = AutoModelForCausalLM.from_pretrained(str(model_dir), torch_dtype=torch.float16,
                                               trust_remote_code=True).to("cuda").eval()
    return tok, mdl


def caption_one(video_path: Path, tok, mdl, max_length: int, include_camera: bool, include_lighting: bool) -> str:
    """Caption a single clip. The exact ShareCaptioner-Video API differs by checkpoint;
    we follow the canonical examples in their repo."""
    # Sample 8 frames uniformly using decord
    import decord
    decord.bridge.set_bridge("torch")
    vr = decord.VideoReader(str(video_path))
    n = len(vr)
    idx = [int(i * (n - 1) / 7) for i in range(8)]
    frames = vr.get_batch(idx)  # (T, H, W, 3) uint8

    instruction_parts = ["Describe the video in detail, including the subjects, actions, and scene."]
    if include_camera: instruction_parts.append("Describe the camera (lens, framing, movement).")
    if include_lighting: instruction_parts.append("Describe the lighting (key, mood, color).")
    instruction = " ".join(instruction_parts)

    # ShareCaptioner-Video expects a chat-template message with the frames; the loader
    # exposes `mdl.chat(...)`. If the API in your install differs, adapt here.
    response = mdl.chat(tokenizer=tok, frames=frames, query=instruction,
                        max_new_tokens=max_length, do_sample=False)
    if isinstance(response, tuple):  # some checkpoints return (text, history)
        response = response[0]
    return response.strip()


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--input", type=Path, required=True, help="directory of mp4/mov clips")
    p.add_argument("--output", type=Path, required=True, help="output JSON path")
    p.add_argument("--captioner", choices=["share-captioner-video", "auroracap"],
                   default="share-captioner-video")
    p.add_argument("--max-length", type=int, default=120)
    p.add_argument("--include-camera", action="store_true")
    p.add_argument("--include-lighting", action="store_true")
    p.add_argument("--extensions", nargs="+", default=[".mp4", ".mov", ".webm", ".mkv"])
    args = p.parse_args()

    clips = sorted([
        p for p in args.input.rglob("*") if p.suffix.lower() in args.extensions
    ])
    if not clips:
        rprint(f"[red]no clips found in {args.input}[/red]"); sys.exit(1)
    rprint(f"[cyan]{len(clips)} clips to caption[/cyan]")

    if args.captioner == "share-captioner-video":
        tok, mdl = load_share_captioner_video()
    else:
        rprint("[yellow]AuroraCap loader not implemented; use share-captioner-video for now.[/yellow]")
        sys.exit(1)

    out = {}
    if args.output.exists():
        out = json.loads(args.output.read_text(encoding="utf-8"))
        rprint(f"[dim]resuming with {len(out)} cached captions[/dim]")

    with torch.inference_mode():
        for clip in track(clips, description="captioning"):
            key = str(clip.relative_to(args.input))
            if key in out: continue
            try:
                out[key] = caption_one(clip, tok, mdl, args.max_length,
                                       args.include_camera, args.include_lighting)
            except Exception as e:
                rprint(f"  [red]fail {key}: {e}[/red]")
                out[key] = ""
            # incremental save
            args.output.write_text(json.dumps(out, indent=2, ensure_ascii=False), encoding="utf-8")

    rprint(f"[green]wrote {args.output} ({len(out)} captions)[/green]")


if __name__ == "__main__":
    main()
