"""
add_audio.py — Adds audio (ambient/foley/music + optional lip-sync) to a video.

Examples:
    # ambient audio from text prompt
    python scripts/add_audio.py --video out/clip.mp4 --prompt "soft wind, distant bell"

    # TTS dialogue + lip-sync
    python scripts/add_audio.py --video out/portrait.mp4 --tts "Hello world." --lipsync
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
import tempfile
from pathlib import Path

from rich import print as rprint

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
CACHE_ROOT = Path(os.environ.get("SEEDANCE_CACHE", Path.home() / ".cache" / "seedance-replica"))


def mmaudio_generate(video: Path, prompt: str, duration: float, out_audio: Path, steps: int = 25, cfg: float = 4.5, seed: int = 42):
    """Run MMAudio video-to-audio."""
    try:
        from mmaudio.eval_utils import generate_audio  # name may differ; see MMAudio repo
        from mmaudio.model.flow_matching import FlowMatching
    except ImportError:
        rprint("[red]mmaudio not installed. pip install git+https://github.com/hkchengrex/MMAudio[/red]")
        sys.exit(1)

    # Pseudocode wrapper — replace with the canonical MMAudio API call.
    # The MMAudio repo exposes a `demo.py`; we shell out to it for portability.
    import shutil
    demo = shutil.which("mmaudio-demo") or str(CACHE_ROOT / "models" / "mmaudio" / "demo.py")
    cmd = [
        sys.executable, demo,
        "--video", str(video),
        "--prompt", prompt,
        "--duration", str(duration),
        "--num_steps", str(steps),
        "--cfg_strength", str(cfg),
        "--seed", str(seed),
        "--output", str(out_audio),
    ]
    rprint(f"[dim]MMAudio: {' '.join(cmd)}[/dim]")
    subprocess.run(cmd, check=True)


def tts_generate(text: str, voice: str, out_audio: Path):
    """Local Piper TTS by default; ElevenLabs if --voice starts with eleven-."""
    if voice.startswith("eleven-") or voice.startswith("elevenlabs-"):
        import requests
        api_key = os.environ.get("ELEVENLABS_API_KEY")
        if not api_key:
            rprint("[red]ELEVENLABS_API_KEY not set[/red]"); sys.exit(1)
        voice_id = voice.split("-", 1)[1]
        resp = requests.post(
            f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}",
            headers={"xi-api-key": api_key, "Content-Type": "application/json"},
            json={"text": text, "model_id": "eleven_turbo_v2_5"},
            timeout=60,
        )
        resp.raise_for_status()
        out_audio.write_bytes(resp.content)
        return
    # Piper local
    piper_model = voice.replace("piper-", "")
    cmd = ["piper", "--model", piper_model, "--output_file", str(out_audio)]
    rprint(f"[dim]piper: {' '.join(cmd)}[/dim]")
    subprocess.run(cmd, input=text.encode(), check=True)


def latentsync(video: Path, audio: Path, out_video: Path):
    """Run LatentSync to re-render mouth region matching audio."""
    weights = CACHE_ROOT / "models" / "latentsync"
    if not weights.exists():
        rprint(f"[red]LatentSync weights missing at {weights}. "
               f"Accept license at https://huggingface.co/ByteDance/LatentSync and re-run download_models.py --preset lipsync[/red]")
        sys.exit(1)
    cmd = [
        sys.executable, str(ROOT / "third_party" / "LatentSync" / "scripts" / "inference.py"),
        "--unet_config_path", str(weights / "configs/unet/stage2.yaml"),
        "--inference_ckpt_path", str(weights / "latentsync_unet.pt"),
        "--video_path", str(video),
        "--audio_path", str(audio),
        "--video_out_path", str(out_video),
    ]
    rprint(f"[dim]LatentSync: {' '.join(cmd)}[/dim]")
    subprocess.run(cmd, check=True)


def mux_audio_to_video(video: Path, audio: Path, out_video: Path):
    """ffmpeg mux."""
    cmd = [
        "ffmpeg", "-y", "-i", str(video), "-i", str(audio),
        "-c:v", "copy", "-c:a", "aac", "-b:a", "192k",
        "-map", "0:v:0", "-map", "1:a:0", "-shortest",
        str(out_video),
    ]
    subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def get_duration(video: Path) -> float:
    out = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "default=noprint_wrappers=1:nokey=1", str(video)],
        check=True, capture_output=True, text=True,
    )
    return float(out.stdout.strip())


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--video", type=Path, required=True)
    p.add_argument("--prompt", help="text prompt for ambient/foley audio")
    p.add_argument("--tts", help="text to speak (dialogue mode)")
    p.add_argument("--voice", default="piper-en_US-amy-medium")
    p.add_argument("--lipsync", action="store_true")
    p.add_argument("--duration", type=float, help="audio length; default = video length")
    p.add_argument("--steps", type=int, default=25)
    p.add_argument("--cfg", type=float, default=4.5)
    p.add_argument("--seed", type=int, default=42)
    p.add_argument("--out", type=Path)
    args = p.parse_args()

    args.out = args.out or args.video.with_stem(args.video.stem + "_audio")
    duration = args.duration or get_duration(args.video)

    with tempfile.TemporaryDirectory() as td:
        td = Path(td)
        if args.tts:
            speech = td / "speech.wav"
            tts_generate(args.tts, args.voice, speech)
            if args.lipsync:
                latentsync(args.video, speech, args.out)
            else:
                mux_audio_to_video(args.video, speech, args.out)
        elif args.prompt:
            ambient = td / "ambient.wav"
            mmaudio_generate(args.video, args.prompt, duration, ambient, args.steps, args.cfg, args.seed)
            mux_audio_to_video(args.video, ambient, args.out)
        else:
            rprint("[red]provide --prompt or --tts[/red]"); sys.exit(1)

    rprint(f"[green]wrote {args.out}[/green]")


if __name__ == "__main__":
    main()
