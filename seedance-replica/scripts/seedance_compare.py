"""
seedance_compare.py — call Higgsfield Seedance 2.0 API for side-by-side comparison.

Usage:
    python scripts/seedance_compare.py --prompt "..." --seed 42 --out out/seedance.mp4

Requires HIGGSFIELD_API_KEY in your env or .env file.
"""

from __future__ import annotations

import argparse
import os
import sys
import time
from pathlib import Path

import requests
from dotenv import load_dotenv
from rich import print as rprint


def main():
    load_dotenv()
    api_key = os.environ.get("HIGGSFIELD_API_KEY")
    if not api_key:
        rprint("[red]HIGGSFIELD_API_KEY not set in env or .env[/red]")
        sys.exit(1)

    p = argparse.ArgumentParser()
    p.add_argument("--prompt", required=True)
    p.add_argument("--seed", type=int, default=42)
    p.add_argument("--duration", type=int, default=5)
    p.add_argument("--resolution", default="720p")
    p.add_argument("--image", type=Path, help="optional first frame")
    p.add_argument("--out", type=Path, required=True)
    args = p.parse_args()

    # NOTE: the exact Higgsfield API surface may evolve. This is the documented
    # shape as of early 2026; check higgsfield.ai/docs if it 404s.
    endpoint = "https://api.higgsfield.ai/v1/seedance/generate"
    payload = {
        "model": "seedance-2.0",
        "prompt": args.prompt,
        "seed": args.seed,
        "duration_s": args.duration,
        "resolution": args.resolution,
    }
    files = {}
    if args.image:
        files["image"] = open(args.image, "rb")

    rprint(f"[cyan]POST {endpoint}[/cyan]")
    r = requests.post(endpoint, headers={"Authorization": f"Bearer {api_key}"},
                      data=payload, files=files, timeout=60)
    r.raise_for_status()
    job = r.json()
    job_id = job["job_id"]
    rprint(f"[dim]job: {job_id}[/dim]")

    # poll
    while True:
        time.sleep(5)
        status = requests.get(f"{endpoint}/{job_id}",
                              headers={"Authorization": f"Bearer {api_key}"}, timeout=30).json()
        rprint(f"[dim]status: {status['state']}[/dim]")
        if status["state"] == "completed":
            video_url = status["output"]["video_url"]
            break
        if status["state"] == "failed":
            rprint(f"[red]Seedance job failed: {status.get('error')}[/red]")
            sys.exit(1)

    rprint(f"[cyan]downloading {video_url}[/cyan]")
    args.out.parent.mkdir(parents=True, exist_ok=True)
    with requests.get(video_url, stream=True, timeout=120) as resp:
        resp.raise_for_status()
        with open(args.out, "wb") as f:
            for chunk in resp.iter_content(chunk_size=1 << 20):
                f.write(chunk)
    rprint(f"[green]wrote {args.out}[/green]")


if __name__ == "__main__":
    main()
