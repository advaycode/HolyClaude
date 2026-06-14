"""CADCopilot MCP server entry point.

A single stdio MCP server that exposes a unified parametric CAD tool set and
dispatches every call to the selected Backend (Inventor COM or Fusion bridge).
Tools, resources and prompts are registered here; the heavy CAD logic lives in
the backends. COM affinity (Inventor is STA) is handled by a dedicated worker
thread set up in Phase 1.
"""

from __future__ import annotations

import sys

from mcp.server.fastmcp import FastMCP

from . import __version__, config

INSTRUCTIONS = """\
You are driving Autodesk Inventor (or Fusion 360) through CADCopilot — parametric
CAD operations exposed as tools. You are the agent; compose the tools to build
anything the user asks, end to end.

OPERATING LOOP (follow it):
1. PLAN. For anything beyond a couple of features, write a plan and a parameter
   table with `scratchpad_update` first: list the bodies/parts, key dimensions as
   named parameters, and the feature order. Read it back with `scratchpad_get`.
2. READ THE KNOWLEDGE. Before modelling for Advay, read the resources:
   `cad://knowledge/inventor-context` (how Advay builds — units, naming, COTS,
   per-archetype recipes), plus `ftc-gobilda-conventions` and `dfm-3dprint-rules`
   when the part is robot/printed. Follow his conventions and DO NOT auto-correct
   his spellings in file/part names.
3. BUILD with parametric primitives. Prefer driving dimensions from named
   parameters (`set_parameter`) so the result is editable. Create entities WITH
   names and reference them by name afterwards.
4. INSPECT + SELF-CORRECT. After every 3-5 operations, call `screenshot` and a
   relevant `list_*`/`measure` to confirm the geometry matches intent. To target
   a fillet/hole/sketch on existing geometry, call `list_faces`/`list_edges`
   first and use the returned semantic names — never guess indices. On failure,
   read `get_last_error` and the `cad://knowledge/error-recovery` resource.
5. REUSE before remodelling. Use `search_parts`/`insert_part` to drop in existing
   goBILDA / vendor / Advay parts, and `run_ilogic_rule` to drive his existing
   parametric parts, instead of modelling COTS from scratch.
6. EXPORT only when asked or when verifying printability; STL/3MF must be
   manifold. Generated files go to the output dir (asked per build), never the
   vault.

UNITS: tool inputs are inches by default (Advay's Inventor workflow); pass a unit
string for metric goBILDA work, e.g. distance_mm or unit="mm". Angles are degrees.

ESCAPE HATCH: for anything the typed tools don't cover (drawings, sheet metal,
surfaces, Design Accelerator, Content Center, advanced joint origins, derive/draft/
split, every work-feature variant), use `execute_script`. The resource
`cad://knowledge/full-api-spec` has the EXACT Inventor COM + Fusion signature for
all ~199 operations — read it and script the call. execute_script is
transaction-wrapped (rolled back on error). For assembly mating prefer
`add_constraint` (mate/flush/insert/angle/tangent); joints need specific origin
geometry (see full-api-spec).
"""

mcp = FastMCP("cad-mcp", instructions=INSTRUCTIONS)


# --------------------------------------------------------------------------- #
# Phase 0 meta tools
# --------------------------------------------------------------------------- #
@mcp.tool()
def ping() -> str:
    """Health check. Confirms the CADCopilot server is alive (does not touch CAD)."""
    return f"cad-mcp v{__version__} alive — backend={config.CAD_BACKEND}"


@mcp.tool()
def cad_status() -> dict:
    """Report server configuration without connecting to the CAD app."""
    return {
        "version": __version__,
        "backend": config.CAD_BACKEND,
        "unit_mode": config.CAD_UNIT_MODE,
        "output_dir": str(config.CAD_OUTPUT_DIR),
        "python": sys.version.split()[0],
    }


# Register the CAD tool surface (documents, sketches, features, inspection, ...)
# and the knowledge resources / prompts (loaded after mcp is defined to avoid a cycle).
from . import resources, tools  # noqa: E402
tools.register(mcp)
resources.register(mcp)


def main() -> None:
    """Console entry point: run the MCP server over stdio."""
    mcp.run()


if __name__ == "__main__":
    main()
