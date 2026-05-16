# HolyClaude

A complete agentic AI stack built and battle-tested by Advay. Every agent is a real Python script. Everything runs locally on Ollama. Fully replicable.

---

## What This Is

HolyClaude is the distilled meta-framework behind every AI project Advay has built:

- **13-source parallel web crawler** with 5-layer + Gemma L6 validation (from GNN-PCNA)
- **Ollama agent base class** — any model, OpenAI-compatible, streaming
- **PromptOptimizer** — classifies task → routes to right model → injects vault context → decomposes
- **KnowledgeWriter** — pushes research to Obsidian knowledge graph as wikilinked Markdown
- **ResearchPipeline** — YouTube (yt-dlp, no API key) → NotebookLM → vault
- **Unified MCP server** — exposes all agents as tools callable from Claude Code
- **UI stack reference** — Streamlit, React, Remotion, ManimGL, Spline, shadcn

---

## Architecture

```
                        ┌─────────────────────────────────────┐
                        │           Claude Code (IDE)         │
                        │    SuperClaude 31 commands           │
                        │    20 specialized agents            │
                        └─────────────┬───────────────────────┘
                                      │ MCP protocol
                         ┌────────────▼────────────┐
                         │      mcp_hub.py          │
                         │  (unified MCP server)   │
                         └──┬──────┬──────┬────────┘
                            │      │      │
              ┌─────────────▼─┐  ┌─▼──────▼────────────────┐
              │PromptOptimizer│  │    Agent Toolkit         │
              │  classify     │  │  CrawlerAgent            │
              │  route        │  │  VerifierAgent (Gemma)   │
              │  compress     │  │  KnowledgeWriter         │
              │  inject vault │  │  ResearchPipeline        │
              └──────┬────────┘  └──────────┬───────────────┘
                     │                      │
         ┌───────────▼──────────────────────▼───────────┐
         │              Ollama (localhost:11434)          │
         │   gemma3:4b  •  qwen2.5:7b  •  mistral:7b    │
         │   OpenAI-compatible API                        │
         └───────────────────────┬───────────────────────┘
                                 │
         ┌───────────────────────▼───────────────────────┐
         │           Obsidian Knowledge Graph             │
         │   C:/Users/advay/Obsidian/Claude/Memory/       │
         │   22 hub notes · 100+ conversations indexed    │
         │   auto-indexed by KnowledgeWriter              │
         └───────────────────────────────────────────────┘
```

---

## Projects This Powers

| Project | Stack | Status |
|---|---|---|
| **GNN-PCNA** | PyTorch Geometric, GATv2Conv, Streamlit, 13-source crawler, Gemma L6 | Model trained, cryptic pockets identified |
| **NeuroLens+** | Eye-tracking, React, Python | Paused |
| **Stock Trader** | Alpaca API, ML signals | Blocked on API keys |
| **OpenMontage** | Remotion, FFmpeg, 52 tools, 12 workflows | Ready |
| **Faceless Pipeline** | AI video factory, revenue tracking | Active |
| **Research Pipeline** | yt-dlp → NotebookLM → vault | Active |
| **Research Program Scraper** | Playwright, AI extraction, scholarship data | Complete |

---

## Agent Catalog

### `OllamaAgent` — `agents/base_agent.py`
Base class for all local LLM agents. Connects to Ollama's OpenAI-compatible API.
```python
from agents import OllamaAgent
agent = OllamaAgent(model="gemma3:4b")
response = agent.chat("Explain focal loss for imbalanced binary classification")
```

### `CrawlerAgent` — `agents/crawler_agent.py`
Multi-source parallel web crawler. 5-layer validation pipeline. Pluggable sources.
```python
from agents import CrawlerAgent, PubMedSource, ArXivSource, ZenodoSource
crawler = CrawlerAgent(
    topic="cryptic protein pockets",
    keywords=["cryptic pocket", "GNN", "PocketMiner", "AlphaFold"],
    output_dir=Path("data/pockets"),
    workers=6,
)
crawler.add_source(PubMedSource(["PCNA cryptic pocket GNN", "sliding clamp allosteric"]))
crawler.add_source(ArXivSource("protein pocket graph neural network"))
crawler.add_source(ZenodoSource(["cryptosite dataset", "pocketminer training data"]))
catalog = crawler.run()
```

### `VerifierAgent` — `agents/verifier_agent.py`
Gemma 3:4b as LLM judge — scores each crawled record 1-10 for relevance.
```python
from agents import VerifierAgent
verifier = VerifierAgent(
    domain="PCNA cryptic pocket prediction",
    scoring_guide="10=direct PCNA data, 7=GNN/pocket methods, 5=general protein, 1=unrelated",
    auto_approve_types=["structure"],
)
catalog_path = verifier.verify_catalog(Path("data/pockets/catalog.json"))
```

### `KnowledgeWriter` — `agents/knowledge_writer.py`
Converts catalog records into wikilinked Obsidian Markdown notes.
```python
from agents import KnowledgeWriter
writer = KnowledgeWriter(
    vault_dir=Path("C:/Users/advay/Obsidian/Research"),
    min_gemma=6,
)
writer.write_catalog(Path("data/pockets/catalog.json"))
```

### `PromptOptimizer` — `agents/prompt_optimizer.py`
Classify → route → compress → inject → chain. The core efficiency engine.
```python
from agents import PromptOptimizer
optimizer = PromptOptimizer(
    vault_dir=Path("C:/Users/advay/Obsidian/Claude/Memory"),
    domain_context="GNN-PCNA cryptic pocket prediction",
    run_local=True,
)
plan = optimizer.optimize("Implement graph construction for PCNA homotrimer")
print(plan.render())   # see routing + vault hits + step breakdown
result = plan.execute()  # run through Ollama
```

### `ResearchPipeline` — `agents/research_pipeline.py`
YouTube (yt-dlp) → NotebookLM → Obsidian vault. No YouTube API key needed.
```python
from agents import ResearchPipeline
pipeline = ResearchPipeline(vault_dir=Path("C:/Users/advay/Obsidian/Research"))
result = pipeline.run(
    topic="PCNA cryptic pocket graph neural network",
    n_videos=6,
    artifact_types=["report", "flashcards"],
)
```

### `mcp_hub.py` — `agents/mcp_hub.py`
Unified MCP server. Register in Claude Code to call all agents as tools.
```bash
# Register in Claude Code MCP settings:
# Name: holy-claude
# Command: python
# Args: C:/Users/advay/HolyClaude/agents/mcp_hub.py
python agents/mcp_hub.py
```

---

## Workflows

### Full research data pipeline
```bash
python workflows/data_pipeline.py \
  --topic "PCNA cryptic pocket prediction" \
  --keywords "cryptic pocket" "GNN" "graph neural network" "PCNA" \
  --sources pubmed arxiv zenodo \
  --verify \
  --vault C:/Users/advay/Obsidian/Research \
  --output data/pcna_research
```

### YouTube → NotebookLM research flow
```bash
python workflows/research_flow.py "protein pocket prediction GNN" \
  --n 6 \
  --artifacts report flashcards mindmap \
  --question "What datasets are available for training pocket prediction models?" \
  --vault C:/Users/advay/Obsidian/Research
```

### Direct Ollama agent (implement / review / debug)
```python
from agents import OllamaAgent
from agents.prompt_optimizer import TASK_ROUTING

agent = OllamaAgent(model="gemma3:4b")
route = TASK_ROUTING["review"]
result = agent.chat(
    open("src/data_processing/parse_pdb.py").read(),
    system=route["prefix"],
)
```

---

## Multi-Agent Role Separation

The pattern from GNN-PCNA — generalized:

| Agent | Role | Does NOT do |
|---|---|---|
| **Claude Code** | Architecture, plans, research reasoning | Implementation, code generation |
| **Gemma 3:4b** (local) | Implementation from plans, code review | Architecture decisions |
| **VerifierAgent** | Credibility scoring of data sources | Repo navigation, coding |
| **NotebookLM** | Research extraction from papers | Coding, architecture |
| **CrawlerAgent** | Multi-source data collection | Analysis, inference |
| **KnowledgeWriter** | Vault persistence | Analysis, generation |

---

## Prompt Efficiency System

See [PROMPT_EFFICIENCY.md](PROMPT_EFFICIENCY.md) for the full system.

The 5-step pipeline:
1. **Classify** — heuristic or LLM task type detection
2. **Route** — match task to optimal model + temperature
3. **Compress** — strip redundant context to key facts
4. **Inject** — pull relevant Obsidian vault notes into context
5. **Chain** — decompose complex tasks into sequential subtasks

---

## Full Stack

See [STACK.md](STACK.md) for complete replication guide including:
- Ollama setup + model pulls
- Python package installation
- MCP server registration in Claude Code
- SuperClaude 31 commands + 20 agents
- yt-research + NotebookLM tool setup
- UI stack (Streamlit, React, Remotion, ManimGL, Spline, shadcn)
- Obsidian vault structure
- Environment variables

---

## Quick Start

```bash
git clone https://github.com/advaycode/HolyClaude
cd HolyClaude
pip install -r requirements.txt

# Start Ollama and pull the model
ollama serve &
ollama pull gemma3:4b

# Register the MCP server in Claude Code
# (see STACK.md section 4)

# Run a research pipeline
python workflows/data_pipeline.py \
  --topic "your research topic" \
  --keywords "key" "terms" \
  --sources pubmed arxiv \
  --verify
```

---

## License

MIT — build on it.

---

*Built by Advay — high school builder. GitHub: [advaycode](https://github.com/advaycode)*
