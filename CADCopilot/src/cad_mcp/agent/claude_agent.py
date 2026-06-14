"""The agent loop behind the in-browser panel: Claude API (Anthropic SDK) drives
the CADCopilot MCP tools, with viewport screenshots fed back as images so Claude
can see the part and self-correct. Zero Claude Code involvement — this talks to
the Claude API directly using ANTHROPIC_API_KEY.
"""

from __future__ import annotations

import asyncio
import os
from pathlib import Path
from typing import Any, Callable

import anthropic

from ..server import mcp  # the configured FastMCP instance (tools + resources)

MODEL = os.environ.get("CAD_CLAUDE_MODEL", "claude-opus-4-8")
EFFORT = os.environ.get("CAD_EFFORT", "medium")   # low|medium|high|max — medium is the cost/quality sweet spot
KEEP_IMAGES = int(os.environ.get("CAD_KEEP_IMAGES", "1"))  # how many recent screenshots to keep in history
KNOWLEDGE = Path(__file__).resolve().parent.parent / "knowledge"

SYSTEM = """\
You are CADCopilot, an expert mechanical-CAD agent driving Autodesk Inventor for
Advay (FTC team Masquerade 4997 / FRC builder). You compose parametric CAD tools to
build anything he asks, end to end, and you watch your work via screenshots.

START EACH BUILD by calling read_cad_knowledge('inventor-context') (how Advay
builds — units, naming, COTS, per-archetype recipes) and read_cad_knowledge(
'workflow-playbook'). For robot/printed parts also read 'ftc-gobilda-conventions'
and 'dfm-3dprint-rules'.

RESEARCH FIRST when the task is a real-world object you lack reliable specs for
(e.g. a fire truck, a specific engine): call web_research("<thing> parts dimensions
proportions") to gather reference context before planning.

LOOP: plan (use scratchpad_update with a parameter table + part list) -> build with
parametric primitives, naming every entity -> VERIFY with cheap tools (measure,
list_bodies, list_faces, bounding_box) and call screenshot SPARINGLY — only at
milestones or when something is wrong, since images cost tokens -> reuse COTS via
search_parts/insert_part and Advay's parametric parts via run_ilogic_rule -> export
manifold STL only when asked or to verify printability.

EFFICIENCY: batch related tool calls; don't re-list geometry you already have;
prefer measure/list_* over screenshots for routine checks. Keep chat replies short.

UNITS: inches by default; pass unit="mm" for goBILDA/FTC metric work. Angles in deg.
TARGETING: to fillet/hole/sketch on existing geometry, call list_faces/list_edges
first and use the returned names — never guess indices; re-list after any feature
that changes the body. ASSEMBLY: prefer add_constraint (mate/flush/insert/angle).
ESCAPE HATCH: for anything the typed tools don't cover, call read_cad_knowledge(
'full-api-spec') for the exact signature, then execute_script.

Be concise in chat; let the tools and screenshots show the work."""

_READ_KNOWLEDGE_TOOL = {
    "name": "read_cad_knowledge",
    "description": "Read a CADCopilot knowledge doc by name: inventor-context, "
                   "workflow-playbook, ftc-gobilda-conventions, dfm-3dprint-rules, "
                   "naming-schema, inventor-api-cheats, error-recovery, full-api-spec.",
    "input_schema": {
        "type": "object",
        "properties": {"name": {"type": "string"}},
        "required": ["name"],
    },
}

# System as a cacheable block — caches tools + system together (render order is
# tools -> system -> messages), so the 67 tool schemas are paid full price once and
# read at ~0.1x on every subsequent step of the agentic loop.
SYSTEM_BLOCKS = [{"type": "text", "text": SYSTEM, "cache_control": {"type": "ephemeral"}}]

_messages: list[dict[str, Any]] = []
_tools_cache: list[dict] | None = None


def reset() -> None:
    _messages.clear()


def _prune_history() -> None:
    """Drop stale screenshots (huge token cost) and over-long knowledge dumps from
    older tool results, keeping only the most recent KEEP_IMAGES screenshots. The
    latest screenshot stays so Claude can still self-correct."""
    tool_msg_idxs = [i for i, m in enumerate(_messages)
                     if m["role"] == "user" and isinstance(m["content"], list)
                     and any(isinstance(b, dict) and b.get("type") == "tool_result" for b in m["content"])]
    keep = set(tool_msg_idxs[-KEEP_IMAGES:]) if KEEP_IMAGES else set()
    for i in tool_msg_idxs:
        if i in keep:
            continue
        for b in _messages[i]["content"]:
            if not (isinstance(b, dict) and b.get("type") == "tool_result"
                    and isinstance(b.get("content"), list)):
                continue
            pruned = []
            for c in b["content"]:
                if isinstance(c, dict) and c.get("type") == "image":
                    pruned.append({"type": "text", "text": "[screenshot omitted to save tokens]"})
                elif isinstance(c, dict) and c.get("type") == "text" and len(c.get("text", "")) > 6000:
                    pruned.append({"type": "text", "text": c["text"][:1200] + "\n…[trimmed to save tokens]"})
                else:
                    pruned.append(c)
            b["content"] = pruned


def _client() -> anthropic.Anthropic:
    if not os.environ.get("ANTHROPIC_API_KEY"):
        raise RuntimeError("ANTHROPIC_API_KEY is not set. Set it in the environment "
                           "(or .mcp.json env) so the panel can reach the Claude API.")
    return anthropic.Anthropic()


def _tools() -> list[dict]:
    global _tools_cache
    if _tools_cache is None:
        mcp_tools = asyncio.run(mcp.list_tools())
        out = [{"name": t.name, "description": (t.description or "")[:2000],
                "input_schema": t.inputSchema} for t in mcp_tools]
        out.append(_READ_KNOWLEDGE_TOOL)
        _tools_cache = out
    return _tools_cache


def _read_knowledge(name: str) -> str:
    p = KNOWLEDGE / f"{name.strip().replace('.md', '')}.md"
    if not p.exists():
        return f"(no knowledge doc named {name!r}; available: " + \
               ", ".join(sorted(x.stem for x in KNOWLEDGE.glob('*.md'))) + ")"
    return p.read_text(encoding="utf-8")


def _mcp_content_to_anthropic(result: Any) -> list[dict]:
    """Convert FastMCP call_tool output (content blocks, possibly an image) into
    Anthropic tool_result content blocks. Images (screenshots) become image blocks
    so Claude can see the viewport."""
    blocks = result[0] if isinstance(result, tuple) else result
    out: list[dict] = []
    try:
        for b in blocks:
            t = getattr(b, "type", None)
            if t == "text":
                out.append({"type": "text", "text": b.text})
            elif t == "image":
                out.append({"type": "image", "source": {
                    "type": "base64", "media_type": getattr(b, "mimeType", "image/png"),
                    "data": b.data}})
            else:
                out.append({"type": "text", "text": str(b)})
    except TypeError:
        out.append({"type": "text", "text": str(blocks)})
    return out or [{"type": "text", "text": "(ok)"}]


def _execute(name: str, tool_input: dict) -> list[dict]:
    if name == "read_cad_knowledge":
        return [{"type": "text", "text": _read_knowledge(tool_input.get("name", ""))}]
    try:
        result = asyncio.run(mcp.call_tool(name, tool_input or {}))
        return _mcp_content_to_anthropic(result)
    except Exception as e:  # noqa: BLE001 - surface tool failure to the model
        return [{"type": "text", "text": f"ERROR: {e}"}]


def run_turn(user_text: str, emit: Callable[[dict], None], max_steps: int = 40) -> None:
    """Run one user turn to completion, emitting events for the browser:
    {type: text|thinking, text}, {type: tool_call, name, input}, {type: image, ...},
    {type: error|done}."""
    client = _client()
    tools = _tools()
    _messages.append({"role": "user", "content": user_text})

    for _ in range(max_steps):
        _prune_history()
        base = dict(model=MODEL, max_tokens=32000, system=SYSTEM_BLOCKS, tools=tools, messages=_messages)
        # Try the most token-efficient config (prompt caching + adaptive thinking +
        # effort) and degrade gracefully if the installed SDK rejects a kwarg.
        for extra in ({"cache_control": {"type": "ephemeral"},
                       "thinking": {"type": "adaptive", "display": "summarized"},
                       "output_config": {"effort": EFFORT}},
                      {"thinking": {"type": "adaptive", "display": "summarized"},
                       "output_config": {"effort": EFFORT}},
                      {"thinking": {"type": "adaptive"}},
                      {}):
            try:
                cm = client.messages.stream(**base, **extra)
                break
            except TypeError:
                continue
        with cm as stream:
            for event in stream:
                if event.type == "content_block_delta":
                    d = event.delta
                    if d.type == "text_delta":
                        emit({"type": "text", "text": d.text})
                    elif d.type == "thinking_delta":
                        emit({"type": "thinking", "text": d.thinking})
            msg = stream.get_final_message()

        _messages.append({"role": "assistant", "content": msg.content})

        if msg.stop_reason != "tool_use":
            if msg.stop_reason == "refusal":
                emit({"type": "error", "text": "Claude declined this request."})
            break

        tool_results = []
        for block in msg.content:
            if block.type == "tool_use":
                emit({"type": "tool_call", "name": block.name, "input": block.input})
                content = _execute(block.name, block.input)
                for c in content:
                    if c["type"] == "image":
                        emit({"type": "image", "media_type": c["source"]["media_type"],
                              "data": c["source"]["data"]})
                tool_results.append({"type": "tool_result", "tool_use_id": block.id,
                                     "content": content})
        _messages.append({"role": "user", "content": tool_results})

    emit({"type": "done"})
