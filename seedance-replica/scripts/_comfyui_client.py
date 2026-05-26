"""
_comfyui_client.py — minimal client used by generate.py for the 'quality' preset.

Talks to a local ComfyUI instance via its /prompt HTTP API and websocket.
Assumes the workflow JSONs from configs/comfyui_workflows/ are saved into
ComfyUI's user workflow directory. If ComfyUI isn't running, this script
starts it as a subprocess.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import time
import urllib.request
import urllib.parse
import uuid
from pathlib import Path

from rich import print as rprint

COMFY_HOST = "127.0.0.1"
COMFY_PORT = 8188
COMFY_DIR = Path(os.environ.get("COMFYUI_DIR", Path.home() / "ComfyUI"))


def _is_alive() -> bool:
    try:
        urllib.request.urlopen(f"http://{COMFY_HOST}:{COMFY_PORT}/system_stats", timeout=2)
        return True
    except Exception:
        return False


def _start_comfy():
    if _is_alive():
        return
    if not (COMFY_DIR / "main.py").exists():
        rprint(f"[red]ComfyUI not found at {COMFY_DIR}. Run install_4070.ps1.[/red]")
        sys.exit(1)
    rprint(f"[dim]starting ComfyUI from {COMFY_DIR}...[/dim]")
    subprocess.Popen(
        [sys.executable, str(COMFY_DIR / "main.py"),
         "--listen", COMFY_HOST, "--port", str(COMFY_PORT), "--highvram"],
        cwd=str(COMFY_DIR),
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    for _ in range(60):
        time.sleep(2)
        if _is_alive():
            rprint("[green]ComfyUI ready[/green]")
            return
    rprint("[red]ComfyUI failed to start within 120s[/red]")
    sys.exit(1)


def _queue_prompt(workflow: dict, client_id: str) -> str:
    data = json.dumps({"prompt": workflow, "client_id": client_id}).encode()
    req = urllib.request.Request(f"http://{COMFY_HOST}:{COMFY_PORT}/prompt", data=data,
                                 headers={"Content-Type": "application/json"})
    return json.loads(urllib.request.urlopen(req).read())["prompt_id"]


def _await_completion(prompt_id: str, timeout: int = 1200) -> dict:
    deadline = time.time() + timeout
    while time.time() < deadline:
        time.sleep(2)
        try:
            hist = urllib.request.urlopen(f"http://{COMFY_HOST}:{COMFY_PORT}/history/{prompt_id}").read()
            data = json.loads(hist)
            if prompt_id in data:
                return data[prompt_id]
        except Exception:
            continue
    raise TimeoutError(f"prompt {prompt_id} did not finish in {timeout}s")


def _load_workflow_template(name: str) -> dict:
    path = COMFY_DIR / "user" / "default" / "workflows" / f"{name}.json"
    if not path.exists():
        rprint(f"[red]workflow {path} not found. See configs/comfyui_workflows/README.md[/red]")
        sys.exit(1)
    return json.loads(path.read_text(encoding="utf-8"))


def run_quality_workflow(args, cfg: dict) -> Path:
    """Run t2v_wan22_gguf workflow with overrides for prompt, seed, resolution, frames."""
    _start_comfy()
    wf = _load_workflow_template("t2v_wan22_gguf")

    # Patch known node IDs. The exact IDs depend on how the user saved the workflow;
    # we look up by class_type. Adjust as needed.
    for node_id, node in wf.items():
        ct = node.get("class_type", "")
        ins = node.setdefault("inputs", {})
        if ct == "CLIPTextEncode" and "positive" in node.get("_meta", {}).get("title", "").lower():
            ins["text"] = args.prompt
        elif ct == "CLIPTextEncode" and "negative" in node.get("_meta", {}).get("title", "").lower():
            ins["text"] = args.negative
        elif ct == "EmptyLatentVideo" or ct == "EmptyHunyuanLatentVideo":
            w, h = cfg["video"]["default_resolution"]
            ins["width"] = w
            ins["height"] = h
            ins["length"] = (args.duration or cfg["video"]["default_duration_s"]) * cfg["video"]["default_fps"]
        elif ct in ("KSampler", "WanMoESampler"):
            ins["seed"] = args.seed
            ins["steps"] = args.num_steps or cfg["sampling"]["num_steps"]
            ins["cfg"] = args.cfg or cfg["sampling"]["cfg_scale"]
            ins["sampler_name"] = cfg["sampling"]["sampler"]
            ins["scheduler"] = cfg["sampling"]["scheduler"]

    client_id = str(uuid.uuid4())
    prompt_id = _queue_prompt(wf, client_id)
    rprint(f"[cyan]ComfyUI prompt queued: {prompt_id}[/cyan]")
    result = _await_completion(prompt_id)

    # Find output video path from history.outputs
    for node_id, out in result.get("outputs", {}).items():
        for vids in out.get("gifs", []) + out.get("videos", []):
            src = COMFY_DIR / "output" / vids["filename"]
            args.out.parent.mkdir(parents=True, exist_ok=True)
            import shutil; shutil.copy2(src, args.out)
            rprint(f"[green]wrote {args.out}[/green]")
            return args.out
    rprint("[red]ComfyUI returned no video output[/red]")
    sys.exit(1)
