"""
multishot.py — generate a multi-shot sequence by chaining I2V with last-frame conditioning.

Usage:
    python scripts/multishot.py --shots shots.json --character-lora aiko.safetensors --out out/seq.mp4

shots.json:
[
  {"prompt": "shot 1 description", "duration": 5, "motion": "static"},
  {"prompt": "shot 2 description", "duration": 5, "motion": "dolly_in"},
  ...
]
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import tempfile
from pathlib import Path

from rich import print as rprint

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))


MOTION_HINTS = {
    "static":   "static locked-off shot",
    "dolly_in": "slow dolly forward toward the subject",
    "dolly_out":"slow dolly backward away from the subject",
    "pan_left": "smooth horizontal pan left",
    "pan_right":"smooth horizontal pan right",
    "push_in":  "gentle push-in toward the subject",
    "orbit":    "slow orbital camera around the subject",
    "tracking": "smooth tracking shot following the subject",
    "tilt_up":  "slow tilt up",
    "tilt_down":"slow tilt down",
    "handheld": "subtle handheld camera, organic motion",
}


def extract_last_frame(video: Path, out_image: Path):
    """ffmpeg dump last frame as PNG."""
    cmd = ["ffmpeg", "-y", "-sseof", "-0.1", "-i", str(video), "-frames:v", "1", "-q:v", "1", str(out_image)]
    subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def concat_videos(videos, out_path: Path, crossfade_frames: int = 6, fps: int = 24):
    """Concatenate clips with optional crossfade. Uses ffmpeg xfade for crossfades."""
    if crossfade_frames <= 0 or len(videos) == 1:
        # simple concat via demuxer
        with tempfile.NamedTemporaryFile("w", suffix=".txt", delete=False) as f:
            for v in videos: f.write(f"file '{v.absolute().as_posix()}'\n")
            list_file = f.name
        cmd = ["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", list_file,
               "-c", "copy", str(out_path)]
        subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        Path(list_file).unlink(missing_ok=True)
        return

    # crossfade chain
    fade_dur = crossfade_frames / fps
    inputs = []
    for v in videos: inputs += ["-i", str(v)]
    n = len(videos)
    filter_lines = []
    last_label = "0:v"
    for i in range(1, n):
        out_label = f"v{i}"
        filter_lines.append(f"[{last_label}][{i}:v]xfade=transition=fade:duration={fade_dur}:offset=PLACEHOLDER[{out_label}]")
        last_label = out_label
    # We can't easily compute offset without probing; fall back to simple concat
    rprint("[yellow]crossfade requires per-clip duration probing; using simple concat for now[/yellow]")
    concat_videos(videos, out_path, crossfade_frames=0, fps=fps)


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--shots", type=Path, required=True)
    p.add_argument("--character-lora", type=Path)
    p.add_argument("--style-lora", type=Path)
    p.add_argument("--preset", choices=["fast", "balanced", "quality"], default="balanced")
    p.add_argument("--crossfade-frames", type=int, default=6)
    p.add_argument("--seed", type=int, default=42)
    p.add_argument("--add-ambient", help="run MMAudio over the final concat with this prompt")
    p.add_argument("--out", type=Path, required=True)
    args = p.parse_args()

    shots = json.loads(args.shots.read_text(encoding="utf-8"))
    rprint(f"[cyan]{len(shots)} shots[/cyan]")

    work = args.out.parent / f"{args.out.stem}_work"
    work.mkdir(parents=True, exist_ok=True)

    shot_videos = []
    last_frame = None
    for i, shot in enumerate(shots, start=1):
        prompt = shot["prompt"]
        if shot.get("motion") in MOTION_HINTS:
            prompt = f"{prompt}, {MOTION_HINTS[shot['motion']]}"

        shot_video = work / f"shot_{i:02d}.mp4"
        cmd = [
            sys.executable, str(ROOT / "scripts" / "generate.py"),
            "--preset", args.preset,
            "--prompt", prompt,
            "--duration", str(shot.get("duration", 5)),
            "--seed", str(args.seed + i),
            "--out", str(shot_video),
        ]
        if args.character_lora:
            cmd += ["--lora", str(args.character_lora), "--lora-weight", "0.85"]
        if args.style_lora:
            cmd += ["--lora", str(args.style_lora), "--lora-weight", "0.7"]
        if last_frame is not None:
            cmd += ["--image", str(last_frame)]
        rprint(f"[cyan]shot {i}/{len(shots)}[/cyan]")
        subprocess.run(cmd, check=True)
        shot_videos.append(shot_video)

        last_frame = work / f"shot_{i:02d}_last.png"
        extract_last_frame(shot_video, last_frame)

    rprint("[cyan]concatenating shots...[/cyan]")
    concat_path = args.out if not args.add_ambient else (work / "concat.mp4")
    concat_videos(shot_videos, concat_path, crossfade_frames=args.crossfade_frames)

    if args.add_ambient:
        rprint("[cyan]running MMAudio over final concat...[/cyan]")
        subprocess.run([
            sys.executable, str(ROOT / "scripts" / "add_audio.py"),
            "--video", str(concat_path),
            "--prompt", args.add_ambient,
            "--out", str(args.out),
        ], check=True)

    rprint(f"[green]done: {args.out}[/green]")


if __name__ == "__main__":
    main()
