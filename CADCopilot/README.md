# CADCopilot

An MCP server that lets Claude build CAD in **Autodesk Inventor** (and **Fusion 360**)
from natural language — the replicable core of Adam CAD: *tools are parametric CAD
operations; the model is the agent that composes them*, with state-inspection +
screenshots + self-correction so it can build complex things end to end.

One unified tool schema dispatches to either backend:
- **Inventor** — in-process `pywin32` COM (primary; STA worker thread, gencache
  early binding, transaction-wrapped ops).
- **Fusion 360** — TCP/JSON client to an in-app add-in that marshals every `adsk`
  call onto Fusion's main thread.

Advay's FTC/FRC/goBILDA conventions and design-for-3D-print rules live in
`src/cad_mcp/knowledge/` and are loaded as MCP resources every session.

## Setup
```powershell
# from the repo root
python -m pip install uv
uv venv .venv --python 3.12
uv pip install --python .venv\Scripts\python.exe "mcp[cli]" pywin32 pillow
```

## Register with Claude Code (user scope — available everywhere)
```powershell
claude mcp add cad-mcp -s user `
  -e PYTHONPATH="C:\Users\advay\Obsidian\CADCopilot\src" `
  -e PYTHONIOENCODING=utf-8 -e CAD_BACKEND=inventor `
  -e CAD_OUTPUT_DIR="C:\Users\advay\Documents\CacheCAD" -e CAD_UNIT_MODE=inch `
  -- "C:\Users\advay\Obsidian\CADCopilot\.venv\Scripts\python.exe" -m cad_mcp.server
```
Have the target Inventor open (it attaches to a running instance, else launches the
newest). For Fusion, set `CAD_BACKEND=fusion` and enable the add-in in
`fusion_addin/`.

## Layout
- `src/cad_mcp/server.py` — FastMCP entry; registers tools/resources/prompts.
- `src/cad_mcp/backends/` — `base.py` (unified ABC) + `inventor_backend.py` + `fusion_backend.py`.
- `src/cad_mcp/units.py` `registry.py` `scratchpad.py` `screenshots.py` `ftc_constants.py`.
- `src/cad_mcp/index/` — parts catalog (metadata + deep COM feature-tree extractor).
- `src/cad_mcp/knowledge/` — the always-loaded conventions/DFM/API resources.
- `fusion_addin/` — the in-Fusion add-in.

## Fusion 360 (second backend)
The add-in is installed at
`%APPDATA%\Autodesk\Autodesk Fusion 360\API\AddIns\cad-mcp-fusion-addin`.
To use Fusion instead of Inventor:
1. Open Fusion → **Utilities ▸ Add-Ins ▸ Scripts and Add-Ins** → enable
   **cad-mcp-fusion-addin** (it pops "listening on 127.0.0.1:9876").
2. Re-register the MCP with `CAD_BACKEND=fusion` (or edit the env in `.mcp.json`).
The add-in marshals every `adsk` call onto Fusion's main thread (a background socket
thread only fires a CustomEvent), so it won't crash Fusion.

## Try it (flagship)
After restarting Claude Code (so the `cad-mcp` tools load), just ask, e.g.
*"build a goBILDA motor-mount bracket and export an STL"* or *"build a V8 engine for
3D printing"*. The agent reads `cad://knowledge/*` and composes the tools.

A scripted end-to-end build (no agent) is in `tests/test_flagship.py`:
```powershell
.venv\Scripts\python.exe -m pytest -m flagship -s     # builds a real bracket + pulley, exports STL
```

## Tests
```powershell
.venv\Scripts\python.exe -m pytest        # 29 tests; live ones attach to / launch Inventor
```
Note: on a **cold** Inventor launch a modal dialog (license/"what's new") can block
automation — have Inventor already open for unattended runs.

