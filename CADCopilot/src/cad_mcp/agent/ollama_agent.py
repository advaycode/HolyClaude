"""Local agent loop powered by Ollama (no cloud, no API key, no cost). Drives the
CADCopilot MCP tools with a local tool-calling model on the user's CPU.

Default model: qwen2.5:14b-instruct (strong open tool-caller). Local models are
text-only, so screenshots are shown to the human but the MODEL self-corrects via
cheap textual inspection tools (list_bodies / measure / list_faces / bounding_box).
"""

from __future__ import annotations

import asyncio
import json
import os
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any, Callable

from ..server import mcp

OLLAMA_URL = os.environ.get("CAD_OLLAMA_URL", "http://127.0.0.1:11434")
MODEL = os.environ.get("CAD_OLLAMA_MODEL", "gpt-oss:20b")
NUM_CTX = int(os.environ.get("CAD_OLLAMA_CTX", "8192"))
STEP_TIMEOUT = int(os.environ.get("CAD_OLLAMA_TIMEOUT", "900"))  # seconds per model step (CPU is slow)
KNOWLEDGE = Path(__file__).resolve().parent.parent / "knowledge"

SYSTEM = """\
You are CADCopilot, a CAD agent driving Autodesk Inventor for Advay (FTC team
Masquerade 4997 / FRC builder) using TOOLS. Build what the user asks, step by step.

RULES:
- Work in SMALL steps. Call ONE tool, read its result, then decide the next call.
- Before building for Advay, call read_cad_knowledge("inventor-context") and
  read_cad_knowledge("workflow-playbook"); for robot/printed parts also
  "ftc-gobilda-conventions" and "dfm-3dprint-rules".
- RESEARCH FIRST when the task is a real-world object you don't have reliable specs
  for (e.g. "build a fire truck", "build a planetary gearbox"): call
  web_research("<thing> parts dimensions proportions") to gather reference context,
  then write a parts list + parameter table to the scratchpad, THEN build.
- Always create entities with a name and reference them by that name later.
- VERIFY with text tools — list_bodies, list_faces, list_edges, measure,
  bounding_box. You cannot see images, so do NOT rely on screenshot to check work
  (the human sees it; you must use the text tools).
- To fillet/hole/sketch on existing geometry, call list_faces/list_edges first and
  use the names returned. Re-list after any feature that changes the body.
- Units: inches by default; pass unit:"mm" for goBILDA/FTC. Angles in degrees.
- If a tool errors, call get_last_error, read read_cad_knowledge("error-recovery"),
  and try the fix. For things the tools can't do, call
  read_cad_knowledge("inventor-api-cheats") then execute_script.
- Keep chat replies short. When the task is done, say so briefly."""

_READ_KNOWLEDGE = {
    "type": "function",
    "function": {
        "name": "read_cad_knowledge",
        "description": "Read a CADCopilot knowledge doc: inventor-context, "
                       "workflow-playbook, ftc-gobilda-conventions, dfm-3dprint-rules, "
                       "naming-schema, inventor-api-cheats, error-recovery.",
        "parameters": {"type": "object",
                       "properties": {"name": {"type": "string"}},
                       "required": ["name"]},
    },
}

_messages: list[dict[str, Any]] = []
_tools_cache: list[dict] | None = None


def reset() -> None:
    _messages.clear()


def _tools() -> list[dict]:
    global _tools_cache
    if _tools_cache is None:
        out = []
        for t in asyncio.run(mcp.list_tools()):
            out.append({"type": "function", "function": {
                "name": t.name,
                "description": (t.description or "")[:1024],
                "parameters": t.inputSchema or {"type": "object", "properties": {}},
            }})
        out.append(_READ_KNOWLEDGE)
        _tools_cache = out
    return _tools_cache


def _read_knowledge(name: str) -> str:
    p = KNOWLEDGE / f"{name.strip().replace('.md', '')}.md"
    if not p.exists():
        return "(unknown doc; available: " + ", ".join(sorted(x.stem for x in KNOWLEDGE.glob('*.md'))) + ")"
    text = p.read_text(encoding="utf-8")
    return text[:6000] + ("\n…[trimmed for local context]" if len(text) > 6000 else "")


def _mcp_to_text(result: Any, emit: Callable[[dict], None]) -> str:
    """Flatten FastMCP tool output to text for the model; push any image to the
    browser so the human still sees it."""
    blocks = result[0] if isinstance(result, tuple) else result
    parts: list[str] = []
    try:
        for b in blocks:
            t = getattr(b, "type", None)
            if t == "text":
                parts.append(b.text)
            elif t == "image":
                emit({"type": "image", "media_type": getattr(b, "mimeType", "image/png"), "data": b.data})
                parts.append("[screenshot shown to the user; verify geometry with list_bodies/measure]")
            else:
                parts.append(str(b))
    except TypeError:
        parts.append(str(blocks))
    return "\n".join(parts)[:6000] or "(ok)"


def _execute(name: str, args: dict, emit: Callable[[dict], None]) -> str:
    if name == "read_cad_knowledge":
        return _read_knowledge(args.get("name", ""))
    try:
        return _mcp_to_text(asyncio.run(mcp.call_tool(name, args or {})), emit)
    except Exception as e:  # noqa: BLE001
        return f"ERROR: {e}"


def _post(payload: dict) -> dict:
    req = urllib.request.Request(
        f"{OLLAMA_URL}/api/chat",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=STEP_TIMEOUT) as r:
        return json.loads(r.read().decode("utf-8"))


def _chat_stream(payload: dict, emit) -> dict:
    """Stream one model step, emitting content/thinking deltas live to the browser
    so the user sees progress immediately. Returns the assembled assistant message
    (content + any tool_calls)."""
    payload = dict(payload)
    payload["stream"] = True
    req = urllib.request.Request(
        f"{OLLAMA_URL}/api/chat",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"})
    content: list[str] = []
    tool_calls: list = []
    role = "assistant"
    with urllib.request.urlopen(req, timeout=STEP_TIMEOUT) as r:
        for raw in r:
            line = raw.decode("utf-8", "ignore").strip()
            if not line:
                continue
            obj = json.loads(line)
            m = obj.get("message") or {}
            if m.get("role"):
                role = m["role"]
            if m.get("thinking"):
                emit({"type": "thinking", "text": m["thinking"]})
            if m.get("content"):
                content.append(m["content"])
                emit({"type": "text", "text": m["content"]})
            if m.get("tool_calls"):
                tool_calls.extend(m["tool_calls"])
            if obj.get("done"):
                break
    out = {"role": role, "content": "".join(content)}
    if tool_calls:
        out["tool_calls"] = tool_calls
    return out


def run_turn(user_text: str, emit: Callable[[dict], None], max_steps: int = 40) -> None:
    # connectivity check
    try:
        urllib.request.urlopen(f"{OLLAMA_URL}/api/tags", timeout=5).read()
    except Exception:
        emit({"type": "error", "text": f"Can't reach Ollama at {OLLAMA_URL}. "
              "Start the Ollama app (system tray) or run `ollama serve`."})
        emit({"type": "done"})
        return

    if not _messages:
        _messages.append({"role": "system", "content": SYSTEM})
    _messages.append({"role": "user", "content": user_text})
    tools = _tools()

    for _ in range(max_steps):
        try:
            msg = _chat_stream({"model": MODEL, "messages": _messages, "tools": tools,
                                "options": {"temperature": 0.2, "num_ctx": NUM_CTX}}, emit)
        except urllib.error.HTTPError as e:
            emit({"type": "error", "text": f"Ollama error: {e.read().decode('utf-8', 'ignore')[:300]} "
                  f"(is the model '{MODEL}' pulled? run: ollama pull {MODEL})"})
            break
        except Exception as e:  # noqa: BLE001
            emit({"type": "error", "text": f"Ollama request failed: {e}"})
            break

        _messages.append({k: msg[k] for k in ("role", "content", "tool_calls") if k in msg})

        tool_calls = msg.get("tool_calls") or []
        if not tool_calls:
            break

        for tc in tool_calls:
            fn = tc.get("function", {})
            name = fn.get("name", "")
            args = fn.get("arguments", {})
            if isinstance(args, str):
                try:
                    args = json.loads(args or "{}")
                except Exception:
                    args = {}
            emit({"type": "tool_call", "name": name, "input": args})
            result = _execute(name, args, emit)
            _messages.append({"role": "tool", "name": name, "content": result})

    emit({"type": "done"})
