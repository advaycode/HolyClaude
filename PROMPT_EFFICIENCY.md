# Prompt Efficiency — The HolyClaude System

How to make every prompt 10x more effective using the full agent stack.

---

## The Core Problem

Raw prompts waste tokens and get mediocre results because:
1. **Wrong model** — asking Claude to do what Gemma should do (or vice versa)
2. **Missing context** — model doesn't know your codebase, domain, constraints
3. **Bad framing** — task type isn't specified, so the model hedges
4. **No decomposition** — complex tasks sent as one blob
5. **No knowledge grounding** — model hallucinates facts your vault already has

---

## The 5-Step Efficiency Pipeline

```
Raw Prompt
    │
    ▼
1. CLASSIFY   → what task type is this? (implement / review / plan / debug / explain)
    │
    ▼
2. ROUTE      → which model handles this best?
    │           (Claude for architecture, Gemma for implementation, local for review)
    ▼
3. COMPRESS   → strip redundant context, surface key facts
    │
    ▼
4. INJECT     → pull relevant Obsidian vault notes into context window
    │
    ▼
5. CHAIN      → break into sequential subtasks if complex
    │
    ▼
Optimized Prompt → execute on target model
```

---

## Model Routing Table

| Task | Model | Temperature | Why |
|---|---|---|---|
| Architecture / design | Claude (cloud) | 0.3 | Needs broad reasoning + creativity |
| Code implementation | Gemma 3:4b (local) | 0.2 | Deterministic, fast, free |
| Code review | Gemma 3:4b (local) | 0.1 | Low temp = critical, conservative |
| Research synthesis | Claude or Gemma | 0.3 | Depends on context size |
| Debugging | Gemma 3:4b (local) | 0.1 | Very low temp = precise fixes |
| Explanation | Claude or Gemma | 0.35 | Needs fluency |
| Credibility scoring | Gemma 3:4b (local) | 0.1 | Binary judgment, low temp |
| Context compression | Gemma 3:4b (local) | 0.1 | Extract facts, no creativity |
| Research extraction | NotebookLM | N/A | Grounded in your sources |

---

## System Prompt Templates by Task

### Implement
```
You are a senior [language] engineer implementing code from a detailed plan.
Stack: [stack details]
Rules:
- Full type hints on all public functions
- No placeholder TODOs — implement completely
- Handle edge case: [specific constraint]
- Return the complete file + one-paragraph change summary
```

### Review
```
You are a code reviewer for [project].
Return a numbered list of issues only (severity: critical | warning | suggestion).
For each: location, description, minimal fix. No redesign suggestions.
Key things to check:
1. [domain-specific check 1]
2. [domain-specific check 2]
```

### Plan
```
You are a software architect.
Create a detailed implementation plan with:
- Goal (one sentence)
- Files to read first
- Step-by-step implementation (numbered)
- Risks + edge cases
- Tests / validation
Do NOT write code. Write the plan only.
```

### Debug
```
You are debugging [project].
Identify the root cause, explain it in 2 sentences, give the minimal fix.
Do NOT redesign. Do NOT add features. Fix only what is broken.
Known bugs: [KNOWN_BUGS.md content]
```

### Compress (context reduction)
```
Compress the following to bullet points of key facts only.
Keep: all numbers, names, function names, file paths, error messages.
Drop: prose, explanations, examples, narrative.
Target: under [N] tokens.
```

---

## Knowledge Injection Patterns

### Pattern 1: Vault-grounded prompt

```python
from agents.prompt_optimizer import PromptOptimizer

optimizer = PromptOptimizer(
    vault_dir=Path("C:/Users/advay/Obsidian/Claude/Memory"),
    domain_context="GNN-PCNA cryptic pocket prediction",
)
plan = optimizer.optimize("Implement the graph construction for PCNA homotrimer")
# plan.vault_snippets = [relevant notes auto-pulled]
# plan.steps[0].render_user() = prompt with context injected
```

### Pattern 2: Manual injection

```
=== CONTEXT: [file/note name] ===
[paste relevant section]
=== END CONTEXT ===

Task: [your actual prompt]
```

### Pattern 3: NotebookLM grounding

For research claims, always ground in NotebookLM:
```
# In NotebookLM notebook on the topic:
"What does [paper] say about [specific claim]?"
→ paste grounded answer into Claude prompt as CONTEXT
```

---

## Decomposition Patterns

### Sequential chain (for implementation)

```
Step 1 → Plan:    "Create a plan for implementing [feature]"
Step 2 → Stub:    "From this plan, create function stubs with type hints only"
Step 3 → Impl:    "Implement this stub: [paste stub]"  ← send to Gemma
Step 4 → Review:  "Review this implementation: [paste code]"  ← send to Gemma
Step 5 → Signoff: "Final review and integration"  ← Claude
```

### Research chain (for learning new domain)

```
Step 1 → YouTube search:  yt-research "topic" -n 8
Step 2 → NotebookLM:      send URLs → generate report
Step 3 → Distill:         Gemma compress report → key facts
Step 4 → Inject:          use facts as context for implementation prompts
Step 5 → Vault:           KnowledgeWriter → Obsidian notes for future prompts
```

### Multi-agent review chain (GNN-PCNA pattern)

```
Claude    → architecture plan (CLAUDE.md role: "Claude's default output is a plan file, not code")
Gemini    → implementation from plan (stubbed files → complete code)
ChatGPT   → review changed files (bugs, data leakage, edge cases)
Gemma L6  → credibility scoring (crawled data, papers, datasets)
NotebookLM → research extraction (paper facts, methods, metrics)
```

---

## Prompt Anti-Patterns to Avoid

| Anti-pattern | Why it fails | Fix |
|---|---|---|
| "Fix my code" (no context) | Model can't know what's wrong | Paste the file + error message |
| "Write a function to..." (no constraints) | Produces generic code | Specify: types, caller, edge cases, existing patterns |
| "Research [topic]" | Model hallucinates | Use NotebookLM with real sources first |
| One giant prompt for a complex feature | Model loses track | Decompose into plan → stub → implement |
| No system prompt | Model hedges, adds disclaimers | Always specify role + rules |
| Asking Claude to implement (expensive) | Costs tokens, slower | Gemma 3:4b is free, fast, and good enough for implementation |
| "Be creative" for code | Creativity = bugs | Temperature 0.1-0.2 for code, 0.3+ for writing |

---

## Token Efficiency Tricks

### 1. Load the smallest relevant context

```python
# BAD: load everything
context = vault_dir.read_all_notes()

# GOOD: load only what's needed
context = optimizer.inject_knowledge("graph construction PCNA homotrimer")
# Returns top 3 relevant notes, not 200
```

### 2. Compress before injecting

```python
long_plan = read_file("docs/plans/2026-05-15_full_architecture.md")
compressed = optimizer.compress_context(long_plan, max_tokens=400)
# 3000 tokens → 400 tokens of key facts
```

### 3. Use structured output

```
Return EXACTLY:
Line 1: <score 1-10>
Line 2: <reason, max 120 chars>
```
vs. asking for a paragraph (3x more tokens, harder to parse).

### 4. Pre-load Claude.md + REPO_MAP.md

In any Claude Code project, these two files are the cheapest way to give Claude full context — read them at session start, not on every prompt.

### 5. Split review from implementation

Never ask the same LLM call to both implement AND review — you get sycophancy. Always use a separate call (or separate model) for review.

---

## The HolyClaude Prompt Optimization CLI

```bash
# Analyze a prompt and see the routing plan
python -c "
from agents.prompt_optimizer import PromptOptimizer
from pathlib import Path
opt = PromptOptimizer(vault_dir=Path('C:/Users/advay/Obsidian/Claude/Memory'))
plan = opt.optimize('Implement graph construction for PCNA homotrimer')
print(plan.render())
"

# Optimize and execute immediately with Ollama
python -c "
from agents.prompt_optimizer import PromptOptimizer
from pathlib import Path
opt = PromptOptimizer(
    vault_dir=Path('C:/Users/advay/Obsidian/Claude/Memory'),
    run_local=True
)
plan = opt.optimize('Review parse_pdb.py for off-by-one errors in residue indexing')
result = plan.execute()
"
```

---

## Full Stack Decision Tree

```
Got a task?
│
├─ Is it research / "find papers about X"?
│   └─ yt-research → NotebookLM → distill → inject → Claude
│
├─ Is it implementation from a clear spec?
│   └─ Gemma 3:4b local (fast, free, deterministic)
│       → ChatGPT review → Claude signoff if needed
│
├─ Is it architecture / "how should we design X"?
│   └─ Claude (cloud) with vault context injected
│       → Plan file → Gemma implements
│
├─ Is it a code review / bug find?
│   └─ Gemma 3:4b (low temp 0.1) → numbered issues only
│
├─ Is it a UI / design task?
│   └─ ui-ux-pro-max skill or frontend-design skill in Claude Code
│       → Tailwind + shadcn + Framer Motion
│       → Spline for 3D, Remotion for video
│
└─ Is it data collection / web scraping?
    └─ CrawlerAgent → VerifierAgent → KnowledgeWriter
        → MCP server exposes to Claude
```
