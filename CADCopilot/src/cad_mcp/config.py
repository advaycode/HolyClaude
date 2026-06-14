"""Runtime configuration, read from the environment set in .mcp.json."""

import os
from pathlib import Path

# Which engine the tools drive: "inventor" (pywin32 COM) or "fusion" (TCP bridge).
CAD_BACKEND: str = os.environ.get("CAD_BACKEND", "inventor").strip().lower()

# Where generated CAD artifacts go. Per Advay's rule, NEVER inside the Obsidian
# vault. Default to the real CacheCAD working area; new_document asks per build.
CAD_OUTPUT_DIR: Path = Path(
    os.environ.get("CAD_OUTPUT_DIR", r"C:\Users\advay\Documents\CacheCAD")
)

# Default unit mode for tool inputs when the caller doesn't pass an explicit unit.
#   "inch"  -> FRC / imperial Inventor workflow (Advay's default in Inventor)
#   "mm"    -> FTC / goBILDA metric workflow
#   "auto"  -> inch unless the active document was created in mm
CAD_UNIT_MODE: str = os.environ.get("CAD_UNIT_MODE", "inch").strip().lower()

# Fusion add-in socket.
FUSION_HOST: str = os.environ.get("CAD_FUSION_HOST", "127.0.0.1")
FUSION_PORT: int = int(os.environ.get("CAD_FUSION_PORT", "9876"))

# Scratchpad / logs live beside generated CAD, never in the vault.
WORK_DIR: Path = CAD_OUTPUT_DIR / ".cad_mcp"

# Inventor type-library GUID (Autodesk Inventor Object Library) for gencache
# early binding — verified present on this machine.
INVENTOR_TYPELIB_GUID = "{D98A091D-3A0F-4C3E-B36E-61F62068D488}"


def ensure_work_dir() -> Path:
    WORK_DIR.mkdir(parents=True, exist_ok=True)
    return WORK_DIR
