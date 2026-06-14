"""Agent backends for the in-browser panel.

CAD_AGENT selects the engine:
  "ollama" (default) — local model on your CPU via Ollama; free, no API key.
  "claude"          — Anthropic Claude API (pay-as-you-go; needs ANTHROPIC_API_KEY).
Both expose run_turn(user_text, emit) and reset().
"""

import os


def get_agent():
    name = os.environ.get("CAD_AGENT", "ollama").strip().lower()
    if name == "claude":
        from . import claude_agent as m
    else:
        from . import ollama_agent as m
    return m
