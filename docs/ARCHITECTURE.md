# HolyClaude — Technical Architecture

Deep dive into the system design, data flows, and key design decisions.

---

## Overview

HolyClaude is organized into five layers:

```
┌─────────────────────────────────────────────────────────────┐
│  Layer 5: Interface                                          │
│  Claude Code IDE · SuperClaude · cli.py · Notebooks         │
├─────────────────────────────────────────────────────────────┤
│  Layer 4: MCP Protocol                                       │
│  mcp_hub.py — 15 tools, FastMCP, JSON-RPC over stdio        │
├─────────────────────────────────────────────────────────────┤
│  Layer 3: Agents                                             │
│  13 specialized agents, all inherit OllamaAgent base        │
├─────────────────────────────────────────────────────────────┤
│  Layer 2: Utilities                                          │
│  TokenBudget · VaultIndex · ResponseCache · ModelRegistry   │
├─────────────────────────────────────────────────────────────┤
│  Layer 1: Infrastructure                                     │
│  Ollama (localhost:11434) · Obsidian Vault · Playwright      │
└─────────────────────────────────────────────────────────────┘
```

---

## Agent Inheritance Hierarchy

```
OllamaAgent (base_agent.py)
│   health_check() · list_models() · chat() · multi_turn()
│   timed_chat() · require_ollama()
│
├── VerifierAgent          — Gemma L6 credibility scoring
├── CodeAgent              — implement / review / plan
├── DiffAgent              — git diff → Ollama review
├── OvernightAgent         — batch scheduler + briefing
│
└── (composition, not inheritance)
    CrawlerAgent           — uses OllamaAgent for optional L6
    ResearchPipeline       — uses PromptOptimizer + yt-research
    StudyAgent             — uses ResearchPipeline
    PlaywrightAgent        — standalone (no Ollama dependency)
    ScholarAgent           — uses PlaywrightAgent
    GraphAgent             — standalone (networkx)
    HubWriter              — standalone (file I/O)
    KnowledgeWriter        — standalone (file I/O)
    PromptOptimizer        — uses OllamaAgent for LLM classify
```

---

## Data Flow: Crawl → Verify → Vault

```
Topic + Keywords
     │
     ▼
CrawlerAgent.run()
     │
     ├── PubMedSource ──────────┐
     ├── ArXivSource ───────────┤  ThreadPoolExecutor (workers=4-6)
     ├── GitHubSource ──────────┤  RateLimiter (1 req/2s per domain)
     ├── ZenodoSource ──────────┤  Retry (×3 exponential backoff)
     └── CustomSource (pluggable)┘
                │
                ▼ SourceRecord dataclass
         ValidationPipeline
                │
                ├── L1: HTTP 200, content-type, timeout=8s
                ├── L2: JSON/XML parse, required fields
                ├── L3: title+abstract length > threshold
                ├── L4: keyword overlap ≥ min_relevance (0.10)
                └── L5: SHA256 dedup, domain allowlist, rate limit
                │
                ▼ passed[] + failed[]
     catalog.json (atomic write via .tmp)
                │
                ▼
     VerifierAgent (optional)
                │
                └── gemma3:4b LLM-as-judge
                    Prompt: "score this record 1-10 for relevance to {domain}"
                    Adds: gemma_score, gemma_reason fields
                    auto_approve_types bypass scoring
                │
                ▼ verified_catalog.json
     HubWriter.write_catalog()
                │
                ├── articles/SLUG.md  (one per record)
                ├── _HUB_ARTICLES.md  (hub note, sorted by relevance)
                └── KNOWLEDGE_GRAPH.md (root node, hub table)
```

### SourceRecord Schema

```python
@dataclass
class SourceRecord:
    uid: str              # unique ID (e.g. "pubmed:12345678")
    record_type: str      # "article" | "preprint" | "dataset" | "code" | "structure"
    source: str           # "PubMed" | "ArXiv" | "Zenodo" | "GitHub"
    url: str
    title: str
    description: str      # abstract or summary
    metadata: dict        # source-specific (pmid, arxiv_id, doi, etc.)
    validation: dict      # L1-L5 results
    passed: bool
    relevance: float      # L4 keyword score
    checksum: str         # SHA256 of content
    fetched_at: str       # ISO datetime
    gemma_score: int      # 1-10, added by VerifierAgent
    gemma_reason: str
```

---

## Data Flow: YouTube → NotebookLM → Vault

```
Topic string
     │
     ▼
search_youtube()  (calls ~/tools/yt-research/yt_research.py)
     │  yt-dlp search, no API key required
     │  Returns: [VideoResult(url, title, channel, duration, views)]
     │
     ▼
Filter by duration (3–45 min), boost quality channels
     │
     ▼
NotebookLM API (unofficial)
     │  Creates notebook with video URLs as sources
     │  Generates artifact: report | video | flashcards | slides | mindmap
     │
     ▼
vault_dir/youtube_research/YYYY-MM-DD_slug.md
     │  Frontmatter: topic, notebook_id, video_urls, artifact_type
     │  Body: embed links, action items, wikilinks
     │
     ▼
ResearchResult(topic, videos, notebook_id, artifacts, vault_notes, generated_at)
```

---

## PromptOptimizer Pipeline

```
Raw prompt string
     │
     ▼  Step 1: Classify
     │   heuristic keyword match → task_type
     │   or: gemma3:4b LLM classify (--llm-classify flag)
     │   task_types: implement | review | research | plan |
     │               debug | explain | compress | ask
     │
     ▼  Step 2: Route
     │   TASK_ROUTING[task_type] →
     │     model: gemma3:4b | gemma3:12b | deepseek-r1:7b
     │     temperature: 0.2 – 0.8
     │     strategy: "direct" | "chain-of-thought" | "decompose"
     │     prefix: specialized system prompt
     │
     ▼  Step 3: Vault Search
     │   _search_vault(vault_dir, keywords) →
     │     keyword overlap scoring across all .md files
     │     returns top-N snippets (500 chars each)
     │
     ▼  Step 4: Assemble PromptPlan
     │   PromptStep(system, user, vault_snippets, model, temperature)
     │   PromptPlan(task_type, routing, steps, vault_snippets)
     │
     ▼  Step 5: Optional decompose
     │   gemma3:4b breaks complex task into subtask steps
     │   each subtask becomes a separate PromptStep
     │
     ▼  plan.render()  →  printable routing summary
        plan.execute() →  runs steps through Ollama sequentially
```

---

## MCP Protocol Integration

```
Claude Code (client)
     │
     │  JSON-RPC over stdio (MCP protocol)
     ▼
mcp_hub.py (FastMCP server)
     │
     │  Tool call: {"name": "run_crawler", "arguments": {...}}
     ▼
agents/*.py (Python agent code)
     │
     ▼
Ollama / Playwright / File I/O / HTTP
     │
     ▼
JSON result → Claude Code context window
```

**Key design:** MCP tools are thin wrappers — all business logic stays in agent classes, not in mcp_hub.py. This keeps agents usable standalone (CLI, scripts, imports) independent of Claude Code.

---

## Validation Pipeline Detail (L1–L6)

| Layer | Name | Check | Failure Action |
|---|---|---|---|
| L1 | Network | HTTP 200, timeout=8s, retry×3 | Skip record |
| L2 | Format | Parse JSON/XML/HTML, required fields exist | Skip record |
| L3 | Content | title+desc non-empty, length threshold | Skip record |
| L4 | Relevance | Keyword overlap ≥ min_relevance | Skip (or keep as "low") |
| L5 | Provenance | SHA256 dedup, domain allowlist, rate limit | Deduplicate |
| L6 | Gemma | LLM scores 1-10 for domain relevance | Filter by min_pass_score |

L1-L5 run in parallel (ThreadPoolExecutor). L6 runs sequentially after L1-L5 (batch API calls).

`auto_approve_types` (e.g. `pdb_structure`) bypass L6 entirely — authoritative sources don't need LLM validation.

---

## Knowledge Graph Schema (Obsidian)

```
vault_dir/
  KNOWLEDGE_GRAPH.md          ← root node, links to all hubs
  _HUB_ARTICLES.md            ← hub: all article notes, sorted by relevance
  _HUB_DATASETS.md
  _HUB_PREPRINTS.md
  _HUB_CODE.md
  articles/
    pubmed_12345678.md        ← one note per record
    arxiv_2401_12345.md
  datasets/
    zenodo_8234567.md
  preprints/
    arxiv_2312_99999.md
  overnight/
    2026-05-16_briefing.md
  youtube_research/
    2026-05-16_gnn_protein.md
```

**Frontmatter schema** (Dataview-compatible):
```yaml
---
type: article
uid: "pubmed:12345678"
title: "PCNA inhibition via cryptic pocket"
source: PubMed
pmid: 12345678
relevance: 0.847
relevance_label: high
gemma_score: 9
project: GNN-PCNA
auto_indexed: 2026-05-16
---
```

---

## Token Budget Strategy

For code implementation tasks (128K context, gemma3:4b):

| Block | Priority | Max Tokens | Content |
|---|---|---|---|
| Task instruction | CRITICAL | 500 | The thing to implement |
| Plan / spec | CRITICAL | 2000 | Implementation plan |
| Repo map | HIGH | 1500 | File tree + key functions |
| Main file | HIGH | 8000 | File being implemented |
| Related files | MEDIUM | 4000 | Dependencies, interfaces |
| Vault context | MEDIUM | 2000 | Relevant research notes |
| Conversation | LOW | 2000 | Prior exchange |
| Response reserve | — | 4096 | Left for model output |

**Total: ~24K tokens used of 131K available** — leaving headroom for iterative refinement.

---

## Rate Limiting

Each source domain gets its own rate limit:

```python
class RateLimiter:
    delays = {
        "pubmed.ncbi.nlm.nih.gov": 0.4,   # NCBI guideline: 3 req/s
        "api.semanticscholar.org": 1.0,
        "export.arxiv.org": 3.0,
        "api.github.com": 0.5,             # 5000 req/hr with token
        "zenodo.org": 1.0,
        "default": 2.0,                    # polite default
    }
```

Retry logic: exponential backoff on 429/503 (×3 max, cap at 32s wait).

---

## Design Decisions

**Why Ollama over API?**
Local inference = no API costs, no rate limits, no privacy concerns for research data. gemma3:4b is strong enough for code review and relevance scoring. Claude handles architecture and reasoning where it matters.

**Why pluggable BaseSource?**
The GNN-PCNA crawler had 13 hardcoded sources. Generalizing to BaseSource lets any project add sources without touching CrawlerAgent. Domain-specific sources stay in their project.

**Why file-based cache?**
SQLite adds a dependency and complicates concurrent access. SHA256-keyed JSON files are inspectable, deletable per-entry, and work across processes. For LLM call caching (where responses are large and calls are rare), file overhead is negligible.

**Why pure-Python community detection?**
Avoiding `python-louvain` dependency (which often conflicts with networkx versions). Label propagation gets 90% of the quality with 0 extra installs.

**Why not stream to MCP?**
MCP tools return complete JSON objects. Streaming is for the CLI/direct API path. The split is clean: `chat(stream=True)` for interactive use, `chat(stream=False, print_stream=False)` for programmatic/MCP use.
