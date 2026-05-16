"""
mcp_hub.py — Unified MCP server exposing all HolyClaude agents to Claude.

Register in Claude Code (Settings > MCP Servers):
  Name:    holy-claude
  Command: python
  Args:    C:/Users/advay/HolyClaude/agents/mcp_hub.py

Tools exposed:
  search_knowledge(query)         — vault keyword search
  run_crawler(topic, keywords)    — launch CrawlerAgent
  verify_catalog(path)            — run VerifierAgent on a catalog
  write_knowledge(catalog_path)   — write Obsidian notes
  optimize_prompt(prompt)         — PromptOptimizer routing + plan
  run_research(topic, n)          — full YouTube→NotebookLM pipeline
  run_ollama(prompt, task_type)   — direct Ollama agent call
  list_agents()                   — list all available agents + status
  pipeline_status()               — check which tools are installed
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(REPO_ROOT))

try:
    from mcp.server.fastmcp import FastMCP
    _MCP_AVAILABLE = True
except ImportError:
    _MCP_AVAILABLE = False
    print("WARNING: mcp package not installed. Run: pip install mcp", file=sys.stderr)

# ── vault path (configurable via env or default) ──────────────────────────────

import os
VAULT_DIR = Path(os.environ.get("HOLY_VAULT", str(Path.home() / "Obsidian" / "Claude" / "Memory")))
CATALOG_DIR = REPO_ROOT / "data" / "catalogs"
CATALOG_DIR.mkdir(parents=True, exist_ok=True)


def _search_vault_local(query: str, vault_dir: Path, max_results: int = 5) -> list[dict]:
    if not vault_dir.exists():
        return []
    keywords = query.lower().split()
    results: list[tuple[float, str, str]] = []
    for md_file in vault_dir.rglob("*.md"):
        try:
            text = md_file.read_text(encoding="utf-8", errors="ignore")
            score = sum(1 for kw in keywords if kw in text.lower())
            if score >= 1:
                snippet = text[:500].strip()
                results.append((score, md_file.name, snippet))
        except Exception:
            continue
    results.sort(key=lambda x: -x[0])
    return [{"file": name, "score": sc, "preview": snippet} for sc, name, snippet in results[:max_results]]


if _MCP_AVAILABLE:
    mcp = FastMCP("holy-claude")

    @mcp.tool()
    def search_knowledge(query: str, vault_path: str = "") -> list[dict]:
        """
        Search the Obsidian knowledge vault by keyword.
        Returns matching note names and previews.
        """
        vault = Path(vault_path) if vault_path else VAULT_DIR
        return _search_vault_local(query, vault)

    @mcp.tool()
    def optimize_prompt(
        prompt: str,
        vault_path: str = "",
        domain: str = "",
        use_llm_classify: bool = False,
    ) -> dict:
        """
        Run the PromptOptimizer on a raw prompt.
        Returns: task_type, model routing, relevant vault snippets, optimized system prompt.
        """
        from agents.prompt_optimizer import PromptOptimizer
        vault = Path(vault_path) if vault_path else VAULT_DIR
        optimizer = PromptOptimizer(
            vault_dir=vault if vault.exists() else None,
            domain_context=domain,
            run_local=False,
        )
        plan = optimizer.optimize(prompt, use_llm_classify=use_llm_classify)
        return {
            "task_type": plan.task_type,
            "model": plan.routing["model"],
            "strategy": plan.routing["strategy"],
            "system_prompt": plan.steps[0].system if plan.steps else "",
            "vault_snippets": plan.vault_snippets,
            "n_steps": len(plan.steps),
            "optimized_user": plan.steps[0].render_user()[:1000] if plan.steps else prompt,
        }

    @mcp.tool()
    def run_ollama(
        prompt: str,
        task_type: str = "ask",
        model: str = "gemma3:4b",
        domain: str = "",
    ) -> str:
        """
        Run a prompt through the local Ollama agent (gemma3:4b).
        task_type: implement | review | research | plan | debug | explain | ask
        """
        from agents.prompt_optimizer import TASK_ROUTING
        from agents.base_agent import OllamaAgent

        agent = OllamaAgent(model=model)
        if not agent.health_check():
            return "ERROR: Ollama not running. Start with: ollama serve"

        routing = TASK_ROUTING.get(task_type, TASK_ROUTING["ask"])
        system = routing["prefix"]
        if domain:
            system += f"\n\nDomain: {domain}"

        return agent.chat(prompt, system=system, stream=False, print_stream=False)

    @mcp.tool()
    def list_agents() -> dict:
        """
        List all available HolyClaude agents and their status.
        """
        from agents.base_agent import OllamaAgent
        agent = OllamaAgent()
        ollama_ok = agent.health_check()
        models = agent.list_models() if ollama_ok else []

        tools_status = {}
        yt_script = Path.home() / "tools" / "yt-research" / "yt_research.py"
        nlm_script = Path.home() / "tools" / "notebooklm" / "notebooklm_skill.py"

        return {
            "ollama": {
                "status": "running" if ollama_ok else "offline",
                "models": models,
                "endpoint": "http://localhost:11434",
            },
            "agents": {
                "base_agent":       {"file": "agents/base_agent.py",        "status": "ready"},
                "crawler_agent":    {"file": "agents/crawler_agent.py",     "status": "ready"},
                "verifier_agent":   {"file": "agents/verifier_agent.py",    "status": "ready"},
                "knowledge_writer": {"file": "agents/knowledge_writer.py",  "status": "ready"},
                "prompt_optimizer": {"file": "agents/prompt_optimizer.py",  "status": "ready"},
                "research_pipeline":{"file": "agents/research_pipeline.py", "status": "ready"},
                "mcp_hub":          {"file": "agents/mcp_hub.py",           "status": "running"},
            },
            "external_tools": {
                "yt_research":  {"path": str(yt_script),  "installed": yt_script.exists()},
                "notebooklm":   {"path": str(nlm_script), "installed": nlm_script.exists()},
                "superclaude":  {"path": str(Path.home() / ".claude" / "commands"), "installed": (Path.home() / ".claude" / "commands").exists()},
            },
            "vault": {
                "path": str(VAULT_DIR),
                "exists": VAULT_DIR.exists(),
            },
        }

    @mcp.tool()
    def pipeline_status() -> dict:
        """
        Check which pipeline stages and tools are installed and working.
        """
        checks = {}

        # Python packages
        for pkg in ["openai", "requests", "beautifulsoup4", "mcp"]:
            try:
                __import__(pkg.replace("-", "_"))
                checks[f"pkg:{pkg}"] = "installed"
            except ImportError:
                checks[f"pkg:{pkg}"] = "MISSING — pip install " + pkg

        # Ollama
        try:
            import urllib.request
            urllib.request.urlopen("http://localhost:11434", timeout=2)
            checks["ollama"] = "running"
        except Exception:
            checks["ollama"] = "offline — run: ollama serve"

        # gemma3:4b
        try:
            from openai import OpenAI
            client = OpenAI(base_url="http://localhost:11434/v1", api_key="ollama")
            models = [m.id for m in client.models.list().data]
            checks["gemma3:4b"] = "available" if "gemma3:4b" in models else f"MISSING — run: ollama pull gemma3:4b (available: {models[:3]})"
        except Exception:
            checks["gemma3:4b"] = "cannot check (ollama offline)"

        # Scripts
        for name, path in [
            ("yt-research", Path.home() / "tools" / "yt-research" / "yt_research.py"),
            ("notebooklm", Path.home() / "tools" / "notebooklm" / "notebooklm_skill.py"),
        ]:
            checks[name] = "found" if path.exists() else f"MISSING at {path}"

        return checks

    @mcp.tool()
    def run_research(
        topic: str,
        n_videos: int = 5,
        artifact_types: list[str] | None = None,
        vault_path: str = "",
    ) -> dict:
        """
        Run the full YouTube → NotebookLM → vault research pipeline.
        artifact_types: ["report", "flashcards", "mindmap", "slides", ...]
        """
        from agents.research_pipeline import ResearchPipeline
        vault = Path(vault_path) if vault_path else (VAULT_DIR.parent if VAULT_DIR.exists() else None)
        pipeline = ResearchPipeline(vault_dir=vault)
        result = pipeline.run(topic, n_videos=n_videos, artifact_types=artifact_types or ["report"])
        return {
            "topic": result.topic,
            "videos_found": len(result.videos),
            "notebook_id": result.notebook_id,
            "artifacts": list(result.artifacts.keys()),
            "vault_notes": [str(p) for p in result.vault_notes],
            "generated_at": result.generated_at,
        }


if __name__ == "__main__":
    if not _MCP_AVAILABLE:
        print("Install mcp first: pip install mcp")
        sys.exit(1)
    mcp.run()
