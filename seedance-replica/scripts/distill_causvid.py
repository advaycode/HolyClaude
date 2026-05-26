"""
distill_causvid.py — CausVid-style 4-step distillation of your LoRA'd checkpoint.

Wraps third_party/CausVid. Expensive (12–24 h on RTX 4070); only run when your
LoRA is stable and you want sub-30s inference.

Usage:
    python scripts/distill_causvid.py \
        --teacher loras/style_v1.safetensors \
        --base wan2.2-ti2v-5b \
        --steps 8000 \
        --student-steps 4 \
        --output loras/style_v1_4step.safetensors
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path

from rich import print as rprint

ROOT = Path(__file__).resolve().parent.parent
CAUSVID = ROOT / "third_party" / "CausVid"


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--teacher", type=Path, required=True, help="LoRA from train_lora.py")
    p.add_argument("--base", default="wan2.2-ti2v-5b")
    p.add_argument("--steps", type=int, default=8000)
    p.add_argument("--student-steps", type=int, default=4)
    p.add_argument("--lr", type=float, default=5e-5)
    p.add_argument("--output", type=Path, required=True)
    args = p.parse_args()

    if not CAUSVID.exists():
        rprint(f"[red]{CAUSVID} not found. Run install_4070.ps1.[/red]")
        sys.exit(1)

    # CausVid's training entry point. Args adapted from its README.
    cmd = [
        sys.executable, str(CAUSVID / "train.py"),
        "--config", str(ROOT / "configs" / "causvid_wan22_4step.yaml"),
        "--teacher_ckpt", str(args.teacher),
        "--student_steps", str(args.student_steps),
        "--max_train_steps", str(args.steps),
        "--learning_rate", str(args.lr),
        "--output_dir", str(args.output.parent),
        "--output_name", args.output.stem,
    ]
    rprint(f"[cyan]launching CausVid: {' '.join(cmd)}[/cyan]")
    rprint("[yellow]This will run for many hours. Use Ctrl+C to interrupt; weights save every 1000 steps.[/yellow]")
    subprocess.run(cmd, check=True)


if __name__ == "__main__":
    main()
