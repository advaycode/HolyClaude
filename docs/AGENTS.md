# Agent API Reference

Full API reference for all HolyClaude agents.

---

## OllamaAgent — `agents/base_agent.py`

Base class for all local LLM agents. All other agents inherit from this.

```python
agent = OllamaAgent(model="gemma3:4b", temperature=0.7, endpoint="http://localhost:11434/v1")
```

| Method | Signature | Description |
|---|---|---|
| `health_check` | `() → bool` | Ping Ollama, return True if running |
| `require_ollama` | `() → None` | Exit with message if Ollama offline |
| `list_models` | `() → list[str]` | Return installed model IDs |
| `chat` | `(prompt, system?, stream?, print_stream?) → str` | Single-turn chat |
| `multi_turn` | `(messages: list[dict]) → str` | Multi-turn with history |
| `timed_chat` | `(prompt, system?) → tuple[str, float]` | Returns (response, elapsed_seconds) |
| `chat_stream` | `(prompt, system?) → Generator` | Raw stream generator |

**Class attributes to override in subclasses:**
```python
class MyAgent(OllamaAgent):
    MODEL = "gemma3:4b"
    TEMPERATURE = 0.5
    MAX_TOKENS = 2048
```

---

## CrawlerAgent — `agents/crawler_agent.py`

Multi-source parallel web crawler with 5-layer validation.

```python
crawler = CrawlerAgent(
    topic="PCNA cryptic pocket",
    keywords=["PCNA", "cryptic", "GNN"],
    output_dir=Path("data/pcna"),
    workers=6,
    min_relevance=0.08,
    save_failed=False,
)
crawler.add_source(PubMedSource(queries=["PCNA allosteric"]))
crawler.add_source(ArXivSource(query="protein pocket GNN"))
catalog = crawler.run()  # → {"passed": [...], "failed": [...], "stats": {...}}
```

**Built-in sources:**

| Source | Class | Config |
|---|---|---|
| PubMed | `PubMedSource(queries: list[str])` | Uses NCBI E-utilities, no key |
| ArXiv | `ArXivSource(query: str, max_results: int)` | Uses export.arxiv.org |
| GitHub | `GitHubSource(queries: list[str])` | Repos only, no token needed |
| Zenodo | `ZenodoSource(queries: list[str])` | Datasets + software |

**Custom source:**
```python
class MySource(BaseSource):
    def fetch(self) -> list[SourceRecord]:
        # Fetch and return records
        return [SourceRecord(uid="...", record_type="article", ...)]
```

---

## VerifierAgent — `agents/verifier_agent.py`

Gemma 3:4b LLM-as-judge for crawled record credibility.

```python
verifier = VerifierAgent(
    domain="PCNA cryptic pocket prediction",
    scoring_guide="10=direct PCNA data, 7=GNN methods, 1=unrelated",
    min_pass_score=6,
    auto_approve_types=["pdb_structure", "structure"],
    model="gemma3:4b",
)

# Single record:
score, reason = verifier.verify_record(record_dict)

# Full catalog (in-place update, atomic write):
verified_path = verifier.verify_catalog(Path("data/catalog.json"))

# Batch:
records = [{"uid": ..., "title": ..., "description": ...}, ...]
scored = verifier.batch_verify(records)
```

---

## HubWriter — `agents/hub_writer.py`

Writes full Obsidian knowledge graph from catalog.

```python
writer = HubWriter(
    vault_dir=Path("C:/Users/advay/Obsidian/Research"),
    project_name="GNN-PCNA",
    min_gemma=6,
    min_relevance=0.08,
    auto_approve_types=["structure", "pdb_structure"],
)

# Full write from catalog:
stats = writer.write_catalog(Path("data/catalog.json"))
# → {"articles": 47, "datasets": 12, "preprints": 8, "total": 67}

# Single record:
writer.write_record(record_dict)

# Custom type handler:
writer.add_type_handler("compound", my_template_fn, subdir="compounds")
```

**Output:**
```
vault_dir/
  KNOWLEDGE_GRAPH.md
  _HUB_ARTICLES.md
  _HUB_DATASETS.md
  articles/pubmed_12345.md
  datasets/zenodo_9876.md
```

---

## PromptOptimizer — `agents/prompt_optimizer.py`

Classify → route → compress → inject vault context → decompose.

```python
optimizer = PromptOptimizer(
    vault_dir=Path("C:/Users/advay/Obsidian/Claude/Memory"),
    domain_context="GNN-PCNA research",
    run_local=True,
    model="gemma3:4b",
)

# Full optimization:
plan = optimizer.optimize(
    "Implement graph construction for PCNA homotrimer",
    use_llm_classify=False,   # heuristic (faster) or LLM
    decompose=True,           # break into subtasks
)

print(plan.render())    # routing summary
plan.execute()          # run through Ollama

# Quick one-shot:
response = optimizer.quick("What is focal loss?")

# Task classification only:
task_type = optimizer.classify_task("review this code")
# → "review"

# Compress a long context:
compressed = optimizer.compress_context(long_text, budget_chars=3000)
```

**Task types and routing:**

| Task | Model | Temp | Strategy |
|---|---|---|---|
| `implement` | gemma3:4b | 0.3 | chain-of-thought |
| `review` | gemma3:4b | 0.2 | direct |
| `plan` | gemma3:4b | 0.5 | decompose |
| `debug` | gemma3:4b | 0.2 | chain-of-thought |
| `research` | gemma3:4b | 0.6 | direct |
| `explain` | gemma3:4b | 0.7 | direct |
| `compress` | gemma3:4b | 0.3 | direct |
| `ask` | gemma3:4b | 0.7 | direct |

---

## CodeAgent — `agents/code_agent.py`

Codebase-aware implement / review / plan agent.

```python
agent = CodeAgent(
    project_root=Path("C:/Users/advay/GNN_PNCA"),
    model="gemma3:4b",
)

# Implement from plan file:
response = agent.implement(Path("docs/plans/parse_pdb.md"))

# Review a source file:
response = agent.review(Path("src/data_processing/graph_builder.py"))

# Generate implementation plan:
response = agent.plan("Implement dual-branch GATv2 with spatial + sequential edges")

# Ask a question about the codebase:
response = agent.ask("How does the DBSCAN clustering work in the Streamlit UI?")

# Review a git diff:
response = agent.diff_review(diff_text)
```

**Project context loaded automatically from:**
- `CLAUDE.md` — project instructions
- `REPO_MAP.md` — file tree + function index
- `KNOWN_BUGS.md` — open issues
- `AGENTS.md` — agent documentation

---

## DiffAgent — `agents/diff_agent.py`

Git-aware code reviewer via Ollama.

```python
agent = DiffAgent(project_root=Path("C:/Users/advay/GNN_PNCA"))

# Review staged changes:
results = agent.review_staged()

# Review branch vs main:
results = agent.review_branch("main")

# Review specific commit:
diff = agent.get_commit_diff("a1b2c3d")
results = agent.review_diff(diff, label="hotfix commit")

# Generate PR summary:
pr_text = agent.generate_pr_summary(results)
```

**ReviewResult fields:** `path`, `severity` (critical/warning/info/ok), `issues: list[str]`, `suggestions: list[str]`, `summary: str`

---

## StudyAgent — `agents/study_agent.py`

Daily topic rotation study pipeline.

```python
# Built-in subjects:
agent = StudyAgent.ap_physics()   # 20 AP Physics 1 topics
agent = StudyAgent.ap_stats()     # 20 AP Statistics topics

# Custom:
agent = StudyAgent.custom(
    topics=["Topic A", "Topic B", "Topic C"],
    subject="My Subject",
)

# Run daily pipeline (auto-rotates topics by date):
result = agent.run_daily(n_videos=4, artifact="video")

# Force a specific topic index:
result = agent.run_daily(force_topic=3)

# Dry run (no NotebookLM):
result = agent.run_daily(dry_run=True)

# Get today's topic without running:
idx, topic = agent.get_todays_topic()
```

**State persistence:** `data/study/{Subject}/state.json` — tracks `last_date` and `topic_index`. Advances one topic per calendar day.

---

## OvernightAgent — `agents/overnight_agent.py`

Batch task scheduler with morning briefing.

```python
agent = OvernightAgent(
    vault_dir=Path("C:/Users/advay/Obsidian"),
    output_dir=Path("data/overnight"),
)

agent.add_research("AlphaFold cryptic pockets", n_videos=5)
agent.add_study(subject="ap-physics", artifact="video")
agent.add_crawl("PCNA GNN dataset", keywords=["PCNA", "dataset"])
agent.add_script(["python", "scripts/update_index.py"])
agent.add_prompt("Summarize today's key findings in GNN-PCNA")

# Sequential:
report = agent.run()

# Parallel (threading):
report = agent.run(parallel=True)

# Load from JSON file:
agent.load_tasks_from_json(Path("tasks/tonight.json"))
```

**Task JSON format:**
```json
[
  {"task_type": "research", "label": "AlphaFold review", "topic": "AlphaFold pocket prediction", "n_videos": 5},
  {"task_type": "study", "subject": "ap-physics", "artifact": "video"},
  {"task_type": "crawl", "topic": "PCNA inhibitor", "keywords": ["PCNA", "drug"]}
]
```

**Output:** JSON report + vault note + Ollama-generated morning briefing.

---

## PlaywrightAgent — `agents/playwright_agent.py`

Browser automation agent for JS-heavy pages.

```python
with PlaywrightAgent(headless=True, block_media=True) as pw:
    # Structured extraction:
    data = pw.scrape_structured(url, schema={
        "title": "h1",
        "abstract": ".abstract",
        "doi": "a.doi@href",      # @attr syntax for attributes
        "date": ".pub-date",
    })

    # Multiple items (list):
    items = pw.scrape_structured(url, schema={...}, multi=True)

    # Extract all links matching pattern:
    links = pw.extract_links(url, pattern=r"arxiv\.org/abs/")

    # Screenshot:
    path = pw.screenshot(url, Path("screenshots/page.png"))

    # Full text:
    text = pw.get_text(url)

    # Batch (parallel workers):
    results = pw.batch_scrape(urls, schema, workers=4)
```

**Schema format:** `{"field": "css_selector"}` or `{"field": "css_selector@attribute"}`

---

## ScholarAgent — `agents/scholar_agent.py`

Multi-source scholarship scraper with eligibility filtering.

```python
agent = ScholarAgent(
    min_amount=500,           # minimum USD award
    deadline_within_days=90,  # only show upcoming deadlines
    headless=True,
)

scholarships = agent.run(output_dir=Path("data/scholarships"))
# → list[Scholarship], also saves catalog.json + CSV

# Write vault notes:
agent.write_vault(scholarships, vault_dir=Path("C:/Users/advay/Obsidian/Scholarships"))

# scholarship.days_until_deadline() → int | None
# scholarship.urgency_label() → "urgent" | "soon" | "open" | "expired" | "unknown"
```

---

## GraphAgent — `agents/graph_agent.py`

Obsidian vault → networkx knowledge graph.

```python
agent = GraphAgent(
    vault_dir=Path("C:/Users/advay/Obsidian"),
    exclude_dirs=[".obsidian", "templates"],
    min_connections=2,
)

graph = agent.build()
agent.print_stats(graph)

# Top nodes by PageRank:
hubs = agent.top_nodes(graph, n=10, metric="pagerank")

# Shortest path:
path = agent.shortest_path(graph, "PCNA", "GNN")
# → ["PCNA", "Cryptic Pockets", "PocketMiner", "GNN"]

# Community members:
members = agent.find_by_community(graph, community_id=0)

# Export for D3.js / visualization:
agent.export_json(graph, Path("data/graph.json"))
```

---

## Utilities

### TokenBudget — `utils/token_budget.py`

```python
budget = TokenBudget(model="gemma3:4b", task_type="implement")
budget.add(ContextBlock(plan_text, Priority.CRITICAL, "plan"))
budget.add(ContextBlock(code, Priority.HIGH, "main_file"))
budget.add(ContextBlock(vault_note, Priority.MEDIUM, "context"))
context = budget.assemble()
print(budget.budget_report())  # utilization stats
```

### VaultIndex — `utils/vault_index.py`

```python
idx = VaultIndex(vault_dir=Path("C:/Users/advay/Obsidian"))
idx.load_or_build()   # loads from cache or builds fresh
idx.save()

results = idx.search("PCNA cryptic pocket", n=5, note_type="article")
for r in results:
    print(f"{r.score:.3f}  {r.note_name}  {r.snippet[:80]}")
```

### ResponseCache — `utils/cache.py`

```python
cache = ResponseCache(default_ttl=3600)   # 1 hour TTL

cached = cache.get(prompt, model="gemma3:4b", system=system)
if cached is None:
    response = agent.chat(prompt, system=system, stream=False, print_stream=False)
    cache.set(prompt, response, model="gemma3:4b", system=system)

print(cache.stats())   # hits, misses, hit_rate, size_kb

# Decorator:
@cache.cached(model="gemma3:4b", system="be concise", ttl=7200)
def summarize(text: str) -> str:
    return agent.chat(text, stream=False, print_stream=False)
```

### ModelRegistry — `configs/models.py`

```python
from configs.models import ModelRegistry

# Auto-select best available model for task:
model = ModelRegistry.select("implement", available=ModelRegistry.available_models())

# Get model info:
info = ModelRegistry.get("gemma3:4b")
print(info.context_tokens)   # 131072
print(info.strengths)        # ["code generation", "instruction following", ...]

# Print full table:
ModelRegistry.print_table()
```
