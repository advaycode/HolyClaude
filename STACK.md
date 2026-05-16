# HolyClaude — Complete Stack & Replication Guide

Full replication from zero to running on any machine.

---

## Prerequisites

| Tool | Version | Install |
|---|---|---|
| Python | 3.10+ | python.org |
| Ollama | latest | [ollama.com](https://ollama.com) |
| Node.js | 18+ | nodejs.org |
| bun | latest | `curl -fsSL https://bun.sh/install \| bash` |
| Git | latest | git-scm.com |
| yt-dlp | latest | `pip install yt-dlp` |

---

## 1. Clone & Install

```bash
git clone https://github.com/advaycode/HolyClaude
cd HolyClaude
pip install -r requirements.txt
```

---

## 2. Ollama Setup (Local LLMs)

```bash
# Install Ollama (Windows)
winget install Ollama.Ollama

# Pull the primary model (4.3B, Q4_K_M, 128K ctx, vision)
ollama pull gemma3:4b

# Optional: pull for comparison
ollama pull qwen2.5:7b
ollama pull mistral:7b

# Start Ollama server (runs on localhost:11434)
ollama serve
```

Verify:
```bash
curl http://localhost:11434/api/tags
```

Ollama exposes an **OpenAI-compatible API** — every agent in this repo uses it via `openai` SDK pointed at `http://localhost:11434/v1`.

---

## 3. Python Agent Stack

```bash
pip install openai requests beautifulsoup4 mcp streamlit torch torch-geometric
pip install yt-dlp notebooklm-py scikit-learn matplotlib pandas
```

### Core Agents

| Agent | File | Purpose |
|---|---|---|
| `OllamaAgent` | `agents/base_agent.py` | Base class — all agents inherit this |
| `CrawlerAgent` | `agents/crawler_agent.py` | Multi-source parallel web crawler + 5-layer validation |
| `VerifierAgent` | `agents/verifier_agent.py` | Gemma 3:4b credibility scorer (L6 of validation pipeline) |
| `KnowledgeWriter` | `agents/knowledge_writer.py` | Writes Obsidian Markdown notes from catalogs |
| `PromptOptimizer` | `agents/prompt_optimizer.py` | Task classify → agent route → knowledge inject → chain |
| `ResearchPipeline` | `agents/research_pipeline.py` | YouTube → NotebookLM → vault pipeline |
| `mcp_hub` | `agents/mcp_hub.py` | Unified MCP server exposing all tools to Claude |

---

## 4. MCP Server Setup (Claude Code Integration)

The `mcp_hub.py` exposes all agents as MCP tools, callable directly from Claude Code.

### Register in Claude Code

Add to `~/.claude/claude_desktop_config.json` (or Claude Code MCP settings):

```json
{
  "mcpServers": {
    "holy-claude": {
      "command": "python",
      "args": ["C:/Users/advay/HolyClaude/agents/mcp_hub.py"],
      "env": {
        "HOLY_VAULT": "C:/Users/advay/Obsidian/Claude/Memory"
      }
    },
    "pcna-vault": {
      "command": "python",
      "args": ["C:/Users/advay/GNN_PNCA/agents/mcp_server.py"]
    }
  }
}
```

### Tools available via MCP

```
search_knowledge(query)            → vault keyword search
optimize_prompt(prompt, domain)    → route + inject + plan
run_ollama(prompt, task_type)      → direct Gemma call
run_research(topic, n_videos)      → YouTube→NotebookLM pipeline
list_agents()                      → status of all tools
pipeline_status()                  → check installed packages
```

---

## 5. SuperClaude Setup

```bash
git clone https://github.com/SuperClaude-Org/SuperClaude_Framework
cd SuperClaude_Framework
python install.py
```

Installs 31 slash commands + 20 agents into `~/.claude/`.

Key commands used in this stack:
- `/sc:implement` — full feature implementation with plan
- `/sc:research` — deep web research
- `/sc:analyze` — code quality + security + performance
- `/sc:build` — build with intelligent error handling
- `/sc:troubleshoot` — root cause diagnosis

On Windows, prefix with:
```
PYTHONIOENCODING=utf-8 python ...
```

---

## 6. Research Pipeline Tools

### yt-research (YouTube without API key)

```bash
mkdir -p ~/tools/yt-research
# Copy yt_research.py to ~/tools/yt-research/
pip install yt-dlp

# Test:
python ~/tools/yt-research/yt_research.py "PCNA protein" -n 5 -f json
```

### NotebookLM (unofficial API)

```bash
pip install notebooklm-py

# Auth (once):
notebooklm login

# Install skill script:
mkdir -p ~/tools/notebooklm
# Copy notebooklm_skill.py to ~/tools/notebooklm/
```

---

## 7. UI Stack

| Tool | Use Case | Install |
|---|---|---|
| **Streamlit** | Python data app UIs (GNN-PCNA predictor) | `pip install streamlit` |
| **React + Vite** | Landing pages, web apps | `bun create vite my-app` |
| **Remotion** | Programmatic video generation | `bun add remotion` |
| **Tailwind CSS** | Utility-first styling | `bun add tailwindcss` |
| **shadcn/ui** | Component library | `bunx shadcn@latest init` |
| **Spline** | 3D web experiences | [spline.design](https://spline.design) |
| **ManimGL** | Math/ML animation (3Blue1Brown style) | `pip install manimgl` |
| **ManimCE** | Math animation (community edition) | `pip install manim` |
| **magic-mcp** | Logo search + shadcn patterns in Claude | `npx @magicpatterns/mcp` |

### UI Patterns Used

- **Glassmorphism** — frosted glass panels with `backdrop-filter: blur`
- **Bento grid** — asymmetric card layouts
- **Dark mode default** — `bg-zinc-950` base
- **Luxury animations** — Framer Motion + CSS custom properties
- **Graph visualization** — D3.js, Three.js, or Plotly
- **DBSCAN clustering UI** — scatter plots with cluster coloring
- **B-factor PDB coloring** — Streamlit + matplotlib heatmap
- **Sequence heatmaps** — per-chain pocket probability strips

---

## 8. Obsidian Memory Web

The Obsidian vault at `C:/Users/advay/Obsidian/` is the knowledge graph.

### Key paths

```
Obsidian/
  Claude/
    Memory/
      _Home.md            ← root hub node
      AI Tools & Agents.md
      SuperClaude & MCP.md
      Research Pipeline.md
      Cybersecurity.md
      Web & Design.md
      ...
    Code/
      neurolens/          ← eye-tracking app
      stock-trader/       ← trading bot
  OpenMontage/            ← agentic video platform
  Claude/Memory/          ← auto-memory (this repo's KnowledgeWriter target)
```

### Writing to vault from agents

```python
from agents import KnowledgeWriter
writer = KnowledgeWriter(vault_dir=Path("C:/Users/advay/Obsidian/Research"))
writer.write_catalog(Path("data/catalog/catalog.json"))
```

---

## 9. GNN-PCNA Agent Pipeline (Domain Example)

Full example of the agent pipeline applied to computational biology:

```
CrawlerAgent (13 sources, parallel)
  → L1 Network → L2 Format → L3 Structural → L4 Biological → L5 Provenance
  → VerifierAgent (Gemma 3:4b, L6 credibility)
  → KnowledgeWriter (Obsidian notes)
  → fetch_structures.py (PDB downloads)
  → build_graphs.py (PyTorch Geometric .pt files)
  → train.py (CrypticGNN / PocketGNN)
  → Streamlit UI (inference + DBSCAN clustering + B-factor export)
  → MCP server (exposes vault + inference to Claude)
```

Run the full pipeline:
```bash
cd C:/Users/advay/GNN_PNCA
python scripts/run_pipeline.py --with-obsidian
```

---

## 10. Environment Variables

```env
HOLY_VAULT=C:/Users/advay/Obsidian/Claude/Memory
OLLAMA_HOST=http://localhost:11434
PYTHONIOENCODING=utf-8
```

Set in `.env` at repo root (never commit):
```bash
cp configs/example.env .env
```

---

## Quick-start Checklist

```
[ ] git clone advaycode/HolyClaude
[ ] pip install -r requirements.txt
[ ] ollama serve (background)
[ ] ollama pull gemma3:4b
[ ] python agents/mcp_hub.py  (register in Claude Code MCP settings)
[ ] notebooklm login
[ ] Copy yt_research.py → ~/tools/yt-research/
[ ] Set HOLY_VAULT in .env
[ ] python workflows/data_pipeline.py --topic "your topic" --keywords "key terms"
[ ] python workflows/research_flow.py "your topic" --n 5
```
