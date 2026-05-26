"""
seedvidebench_lite.py — lightweight evaluation across a subset of SeedVideoBench /
VBench prompts so you can track replica quality against your own baseline.

Usage:
    python benchmarks/seedvidebench_lite.py --preset balanced --out runs/eval_2026-05.json
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from pathlib import Path
from typing import Optional

from rich import print as rprint
from rich.progress import track

ROOT = Path(__file__).resolve().parent.parent

# A curated subset (28 prompts). Categories chosen to overlap SeedVideoBench dimensions.
PROMPTS = [
    # subject motion
    ("motion", "a hummingbird hovers near a red trumpet flower, wings blurred"),
    ("motion", "a wave crashes against a rocky cliff in slow motion"),
    ("motion", "a chef tosses a stir-fry pan, flames leaping briefly"),
    # camera motion
    ("camera", "a slow dolly forward into a candlelit medieval banquet hall"),
    ("camera", "an aerial drone pan over a misty redwood forest at dawn"),
    ("camera", "a whip pan from a violin to the conductor's face"),
    # complex scene
    ("scene", "a rainy Tokyo crosswalk at night, hundreds of pedestrians, neon reflected in puddles"),
    ("scene", "a Saturn-like ringed planet rises over a desert horizon at twilight"),
    # human / facial
    ("human", "a young woman with freckles laughs softly, soft window light, medium shot"),
    ("human", "an old fisherman repairs a net in his lap, weathered hands, golden hour"),
    # animation / stylized
    ("style", "a red origami crane unfolds into a living bird mid-flight, Miyazaki style"),
    ("style", "a black-and-white silent film of a clown juggling apples, 1920s grain"),
    # text / prompt adherence
    ("adherence", "a sign that reads 'OPEN 24 HOURS' flickers in the rain"),  # text is hard
    ("adherence", "exactly three identical cats sit in a row on a windowsill"),
    # physics
    ("physics", "a glass of red wine shatters on a marble floor in slow motion"),
    ("physics", "a single drop of water hits a still pond, ripples spread outward"),
    # multi-shot (single shot here; multishot tested separately)
    ("composition", "wide shot of a lighthouse on a stormy cliff, then push in to the lamp at the top"),
    # I2V
    ("i2v", "the subject in the reference image slowly turns and smiles"),
    # audio sensitivity (for V+A eval)
    ("audio", "rain on a tin roof, distant thunder, candle flickering on a wooden table"),
    # long
    ("long", "a single continuous shot of a chef preparing sushi from start to finish"),
    # stress
    ("stress", "a crowd of a thousand people doing the wave in a stadium at sunset"),
    ("stress", "an underwater coral reef teeming with fish of dozens of species"),
    # color
    ("color", "a pure monochromatic red room with a single white chair"),
    ("color", "a sunset over an alkaline lake, the water tinted pink"),
    # texture
    ("texture", "close-up of bread dough being kneaded, flour dust suspended in light"),
    ("texture", "wet asphalt reflecting neon signs, water droplets on the camera lens"),
    # emotional
    ("emotion", "a child receives a puppy as a gift, tears of joy in slow motion"),
    ("emotion", "an empty playground at dusk, a single swing moving in the wind"),
]


def vbench_score(video_path: Path, dimensions: Optional[list] = None) -> dict:
    """Run VBench scoring on a single video. Stubbed; integrate with vbench python pkg
    when running. Returns {dimension: score} dict."""
    try:
        import vbench  # noqa: F401
    except ImportError:
        return {"_note": "vbench not installed; pip install vbench to enable"}
    # actual call would look like:
    # from vbench import VBench
    # scorer = VBench(...); return scorer.evaluate_single(video_path, dimensions)
    return {"placeholder": 0.0}


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--preset", choices=["fast", "balanced", "quality"], default="balanced")
    p.add_argument("--prompts", type=Path, help="optional JSON of [{category, prompt}]; uses built-in by default")
    p.add_argument("--limit", type=int, help="limit number of prompts")
    p.add_argument("--out", type=Path, required=True)
    p.add_argument("--out-dir", type=Path, default=ROOT / "out" / "bench")
    args = p.parse_args()

    prompts = PROMPTS
    if args.prompts and args.prompts.exists():
        prompts = [(d["category"], d["prompt"]) for d in json.loads(args.prompts.read_text())]
    if args.limit:
        prompts = prompts[:args.limit]

    args.out_dir.mkdir(parents=True, exist_ok=True)
    results = {"preset": args.preset, "started": time.time(), "prompts": []}

    for i, (cat, pr) in enumerate(track(prompts, description="benchmarking")):
        clip = args.out_dir / f"{i:03d}_{cat}.mp4"
        t0 = time.time()
        try:
            subprocess.run([
                sys.executable, str(ROOT / "scripts" / "generate.py"),
                "--preset", args.preset,
                "--prompt", pr,
                "--seed", "42",
                "--out", str(clip),
            ], check=True)
            ok = True
        except subprocess.CalledProcessError as e:
            ok = False
            rprint(f"[red]gen failed for {pr!r}: {e}[/red]")
        elapsed = time.time() - t0
        scores = vbench_score(clip) if ok else {}
        results["prompts"].append({
            "category": cat, "prompt": pr, "video": str(clip),
            "wall_s": round(elapsed, 1), "ok": ok, "scores": scores,
        })
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(json.dumps(results, indent=2), encoding="utf-8")

    rprint(f"[green]wrote {args.out}[/green]")
    rprint(f"  avg wall time: {sum(p['wall_s'] for p in results['prompts'])/len(results['prompts']):.1f}s")


if __name__ == "__main__":
    main()
