"""
side_by_side.py — stitch two videos side-by-side for visual comparison.

Usage:
    python scripts/side_by_side.py --left mine.mp4 --right seedance.mp4 --out compare.mp4
"""

from __future__ import annotations

import argparse
import subprocess
from pathlib import Path


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--left", type=Path, required=True)
    p.add_argument("--right", type=Path, required=True)
    p.add_argument("--label-left", default="Ours (RTX 4070)")
    p.add_argument("--label-right", default="Seedance 2.0 (Higgsfield)")
    p.add_argument("--out", type=Path, required=True)
    args = p.parse_args()

    # hstack with text labels overlaid on each side
    flt = (
        f"[0:v]drawtext=text='{args.label_left}':x=10:y=10:fontsize=24:fontcolor=white:box=1:boxcolor=black@0.5[L];"
        f"[1:v]drawtext=text='{args.label_right}':x=10:y=10:fontsize=24:fontcolor=white:box=1:boxcolor=black@0.5[R];"
        f"[L][R]hstack=inputs=2[V]"
    )
    cmd = [
        "ffmpeg", "-y",
        "-i", str(args.left),
        "-i", str(args.right),
        "-filter_complex", flt,
        "-map", "[V]",
        "-c:v", "libx264", "-crf", "18",
        str(args.out),
    ]
    subprocess.run(cmd, check=True)
    print(f"wrote {args.out}")


if __name__ == "__main__":
    main()
