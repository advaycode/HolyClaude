"""
build_webdataset.py — pack a directory of clips + captions into webdataset tar shards.

Usage:
    python scripts/build_webdataset.py \
        --videos data/my_clips/ \
        --captions data/my_clips_captions.json \
        --output data/my_clips_wds/ \
        --shard-size 1000
"""

from __future__ import annotations

import argparse
import json
import tarfile
import uuid
from pathlib import Path

from rich import print as rprint
from rich.progress import track


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--videos", type=Path, required=True)
    p.add_argument("--captions", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    p.add_argument("--shard-size", type=int, default=1000)
    p.add_argument("--extensions", nargs="+", default=[".mp4", ".mov"])
    args = p.parse_args()

    args.output.mkdir(parents=True, exist_ok=True)
    captions = json.loads(args.captions.read_text(encoding="utf-8"))

    clips = sorted([p for p in args.videos.rglob("*") if p.suffix.lower() in args.extensions])
    rprint(f"[cyan]packing {len(clips)} clips into shards of {args.shard_size}[/cyan]")

    shard_idx = 0
    in_shard = 0
    tar = None
    for clip in track(clips, description="packing"):
        if in_shard == 0:
            tar_path = args.output / f"shard_{shard_idx:04d}.tar"
            tar = tarfile.open(tar_path, "w")

        key = clip.relative_to(args.videos).as_posix().replace("/", "_").rsplit(".", 1)[0]
        # video
        tar.add(clip, arcname=f"{key}.mp4")
        # caption
        cap = captions.get(clip.relative_to(args.videos).as_posix(), "")
        info = tarfile.TarInfo(name=f"{key}.txt")
        body = cap.encode("utf-8")
        info.size = len(body)
        import io
        tar.addfile(info, io.BytesIO(body))

        in_shard += 1
        if in_shard >= args.shard_size:
            tar.close()
            shard_idx += 1
            in_shard = 0

    if tar is not None and in_shard > 0:
        tar.close()

    rprint(f"[green]wrote {shard_idx + (1 if in_shard else 0)} shards to {args.output}[/green]")


if __name__ == "__main__":
    main()
