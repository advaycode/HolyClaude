"""Register the knowledge/*.md files as MCP resources (cad://knowledge/<name>) and
a couple of build prompts, so the agent loads "how Advay builds" every session."""

from __future__ import annotations

from pathlib import Path

KNOW = Path(__file__).parent / "knowledge"


def _register_resource(mcp, path: Path, name: str) -> None:
    uri = f"cad://knowledge/{name}"

    @mcp.resource(uri, name=name, description=f"CADCopilot knowledge: {name}", mime_type="text/markdown")
    def _read() -> str:  # noqa: ANN202
        return path.read_text(encoding="utf-8")


def register(mcp) -> None:
    for md in sorted(KNOW.glob("*.md")):
        _register_resource(mcp, md, md.stem)

    @mcp.prompt()
    def plan_build(goal: str) -> str:
        """Scaffold a plan for building <goal> with CADCopilot."""
        return (
            f"Build this in Inventor with CADCopilot: {goal}\n\n"
            "First read cad://knowledge/workflow-playbook and cad://knowledge/inventor-context. "
            "Then: (1) write a parameter table + part list to the scratchpad; "
            "(2) build each part with parametric primitives, naming every entity; "
            "(3) screenshot + measure every few ops to self-correct; "
            "(4) reuse COTS via search_parts/insert_part where possible; "
            "(5) for printed parts apply DFM clearances and export manifold STL."
        )

    @mcp.prompt()
    def debug_failed_op() -> str:
        """Help recover from a failed CAD operation."""
        return (
            "An operation failed. Call get_last_error, then consult "
            "cad://knowledge/error-recovery and retry with the suggested fix. "
            "Re-run list_faces/list_edges to retarget by fresh names if geometry changed."
        )
