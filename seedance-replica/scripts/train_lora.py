"""
train_lora.py — thin wrapper around musubi-tuner with 4070-safe defaults.

Usage:
    python scripts/train_lora.py --data data/my_clips/ --captions data/my_clips_captions.json \
        --base wan2.2-ti2v-5b --rank 32 --steps 4000 --output loras/style_v1.safetensors
"""

from __future__ import annotations

import argparse
import os
import shlex
import subprocess
import sys
from pathlib import Path

from rich import print as rprint

ROOT = Path(__file__).resolve().parent.parent
CACHE_ROOT = Path(os.environ.get("SEEDANCE_CACHE", Path.home() / ".cache" / "seedance-replica"))

# Map our "base" aliases to musubi-tuner model identifiers
BASE_MAP = {
    "wan2.2-ti2v-5b": {
        "trainer_module": "musubi_tuner.wan_train_network",
        "model_path": CACHE_ROOT / "models" / "wan22_5b",
        "model_type": "wan2.2-ti2v-5b",
        "default_resolution": 720,
        "default_num_frames": 81,
    },
    "wan2.2-t2v-14b": {
        "trainer_module": "musubi_tuner.wan_train_network",
        "model_path": CACHE_ROOT / "models" / "wan22_14b_gguf",
        "model_type": "wan2.2-t2v-14b",
        "default_resolution": 480,
        "default_num_frames": 65,
    },
}


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--data", type=Path, required=True, help="directory of clips OR webdataset shards")
    p.add_argument("--captions", type=Path, help="JSON from caption_video.py")
    p.add_argument("--base", choices=list(BASE_MAP), default="wan2.2-ti2v-5b")
    p.add_argument("--rank", type=int, default=32)
    p.add_argument("--alpha", type=int, default=32)
    p.add_argument("--steps", type=int, default=4000)
    p.add_argument("--lr", type=float, default=1e-4)
    p.add_argument("--warmup", type=int, default=200)
    p.add_argument("--scheduler", default="cosine")
    p.add_argument("--batch-size", type=int, default=1)
    p.add_argument("--grad-accum", type=int, default=4)
    p.add_argument("--resolution", type=int)
    p.add_argument("--num-frames", type=int)
    p.add_argument("--fp8", action="store_true")
    p.add_argument("--blocks-to-swap", type=int, default=20)
    p.add_argument("--save-every", type=int, default=1000)
    p.add_argument("--output", type=Path, required=True)
    p.add_argument("--extra", default="", help="extra args appended to musubi command")
    args = p.parse_args()

    cfg = BASE_MAP[args.base]
    args.resolution = args.resolution or cfg["default_resolution"]
    args.num_frames = args.num_frames or cfg["default_num_frames"]

    args.output.parent.mkdir(parents=True, exist_ok=True)

    # Build the musubi-tuner command. musubi takes a TOML/YAML dataset config and a
    # set of training args. We generate a minimal dataset config on the fly.
    ds_cfg = args.output.parent / f"{args.output.stem}_dataset.toml"
    _write_dataset_toml(ds_cfg, args)
    rprint(f"[dim]dataset config: {ds_cfg}[/dim]")

    cmd = [
        sys.executable, "-m", cfg["trainer_module"],
        "--dit", str(cfg["model_path"]),
        "--dataset_config", str(ds_cfg),
        "--network_module", "networks.lora",
        "--network_dim", str(args.rank),
        "--network_alpha", str(args.alpha),
        "--learning_rate", str(args.lr),
        "--max_train_steps", str(args.steps),
        "--lr_warmup_steps", str(args.warmup),
        "--lr_scheduler", args.scheduler,
        "--gradient_accumulation_steps", str(args.grad_accum),
        "--save_every_n_steps", str(args.save_every),
        "--mixed_precision", "fp16",
        "--output_dir", str(args.output.parent),
        "--output_name", args.output.stem,
        "--blocks_to_swap", str(args.blocks_to_swap),
        "--save_state",
        "--logging_dir", str(ROOT / "runs"),
    ]
    if args.fp8:
        cmd += ["--fp8_base", "--fp8_scaled"]
    if args.extra:
        cmd += shlex.split(args.extra)

    rprint(f"[cyan]launching: {' '.join(cmd)}[/cyan]")
    subprocess.run(cmd, check=True)


def _write_dataset_toml(path: Path, args):
    body = f"""[general]
resolution = [{args.resolution}, {args.resolution}]
caption_extension = ".txt"
batch_size = {args.batch_size}
enable_bucket = true

[[datasets]]
video_directory = "{args.data.as_posix()}"
caption_directory = "{args.data.as_posix()}"
target_frames = [{args.num_frames}]
frame_extraction = "head"
"""
    path.write_text(body, encoding="utf-8")

    # If caption JSON is provided, materialize per-clip .txt files next to each clip.
    if args.captions and args.captions.exists():
        import json
        captions = json.loads(args.captions.read_text(encoding="utf-8"))
        for rel, txt in captions.items():
            clip = args.data / rel
            if not clip.exists(): continue
            (clip.with_suffix(".txt")).write_text(txt or "", encoding="utf-8")


if __name__ == "__main__":
    main()
