"""
prompt_optimizer.py — Multi-agent prompt efficiency pipeline.

Takes a raw user prompt and transforms it through:
  1. Task classification   — what kind of task is this?
  2. Agent routing         — which model should handle it?
  3. Context compression   — strip redundant context, surface relevant facts
  4. Knowledge injection   — pull relevant Obsidian vault notes
  5. Chain construction    — build the optimal prompt chain

The output is a PromptPlan: which agent to use, the optimized prompt,
pre-flight context, and a decomposed subtask list for multi-step work.

Usage:
    optimizer = PromptOptimizer(vault_dir=Path("docs/knowledge"))
    plan = optimizer.optimize("Implement the graph construction module for PCNA")
    print(plan.render())

    # Run through Ollama:
    optimizer = PromptOptimizer(vault_dir=Path("docs/knowledge"), run_local=True)
    plan = optimizer.optimize("Review parse_pdb.py for off-by-one errors")
    result = plan.execute()
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from .base_agent import OllamaAgent


# ── task types and routing table ──────────────────────────────────────────────

TASK_ROUTING: dict[str, dict] = {
    "implement": {
        "model": "gemma3:4b",
        "temperature": 0.2,
        "strategy": "step-by-step implementation from plan",
        "prefix": "You are a senior engineer implementing code from a detailed plan. Return complete, runnable code.",
    },
    "review": {
        "model": "gemma3:4b",
        "temperature": 0.1,
        "strategy": "critical code review — numbered issues only",
        "prefix": "You are a code reviewer. Return a numbered list of issues (critical|warning|suggestion) only. No redesign.",
    },
    "research": {
        "model": "gemma3:4b",
        "temperature": 0.3,
        "strategy": "research synthesis from knowledge base",
        "prefix": "You are a research analyst. Synthesize the provided context into a structured summary.",
    },
    "plan": {
        "model": "gemma3:4b",
        "temperature": 0.25,
        "strategy": "architecture planning with explicit steps",
        "prefix": "You are a software architect. Create a detailed implementation plan with numbered steps.",
    },
    "debug": {
        "model": "gemma3:4b",
        "temperature": 0.1,
        "strategy": "root cause analysis with minimal fix",
        "prefix": "You are debugging code. Identify the root cause, explain it concisely, give the minimal fix.",
    },
    "explain": {
        "model": "gemma3:4b",
        "temperature": 0.3,
        "strategy": "clear explanation with examples",
        "prefix": "You are an expert teacher. Explain this concept clearly with concrete examples.",
    },
    "compress": {
        "model": "gemma3:4b",
        "temperature": 0.1,
        "strategy": "context compression — extract key facts only",
        "prefix": "Compress the following text to bullet points of key facts only. Keep all numbers, names, and technical terms.",
    },
    "ask": {
        "model": "gemma3:4b",
        "temperature": 0.2,
        "strategy": "direct Q&A",
        "prefix": "Answer concisely. Use bullet points and code blocks where helpful.",
    },
}

# Keywords that map to task types
TASK_KEYWORDS: dict[str, list[str]] = {
    "implement": ["implement", "write", "code", "create", "build", "add feature", "stub"],
    "review": ["review", "check", "audit", "critique", "find bugs", "issues", "problems with"],
    "research": ["research", "find papers", "literature", "what does the paper", "summarize research"],
    "plan": ["plan", "design", "architecture", "how should we", "outline", "approach for"],
    "debug": ["debug", "fix", "broken", "error", "fails", "wrong output", "exception"],
    "explain": ["explain", "what is", "how does", "why is", "help me understand", "what does"],
    "compress": ["compress", "summarize", "tldr", "shorten", "condense"],
}


# ── vault search ──────────────────────────────────────────────────────────────

def _search_vault(query: str, vault_dir: Path, max_results: int = 3) -> list[str]:
    """Return content snippets from vault notes matching query keywords."""
    if not vault_dir.exists():
        return []
    keywords = query.lower().split()
    results: list[tuple[float, str]] = []

    for md_file in vault_dir.rglob("*.md"):
        if md_file.stem in ("INDEX", "MEMORY", "_Home"):
            continue
        try:
            text = md_file.read_text(encoding="utf-8", errors="ignore")
            text_lower = text.lower()
            score = sum(1 for kw in keywords if kw in text_lower)
            if score >= 2:
                snippet = text[:600].strip()
                results.append((score, f"[{md_file.stem}]\n{snippet}"))
        except Exception:
            continue

    results.sort(key=lambda x: -x[0])
    return [content for _, content in results[:max_results]]


# ── prompt chain ──────────────────────────────────────────────────────────────

@dataclass
class PromptStep:
    task_type: str
    system: str
    user: str
    model: str
    temperature: float
    context_snippets: list[str] = field(default_factory=list)

    def render_user(self) -> str:
        parts = []
        if self.context_snippets:
            parts.append("=== RELEVANT CONTEXT ===")
            parts.extend(self.context_snippets)
            parts.append("=== END CONTEXT ===\n")
        parts.append(self.user)
        return "\n\n".join(parts)


@dataclass
class PromptPlan:
    raw_prompt: str
    task_type: str
    steps: list[PromptStep]
    routing: dict
    vault_snippets: list[str] = field(default_factory=list)
    _agent: Optional["PromptOptimizer"] = field(default=None, repr=False)

    def render(self) -> str:
        lines = [
            f"Task type:   {self.task_type}",
            f"Model:       {self.routing['model']}",
            f"Strategy:    {self.routing['strategy']}",
            f"Vault hits:  {len(self.vault_snippets)}",
            f"Steps:       {len(self.steps)}",
            "",
        ]
        for i, step in enumerate(self.steps, 1):
            lines.append(f"--- Step {i}: {step.task_type} ---")
            lines.append(f"System: {step.system[:100]}...")
            lines.append(f"User:   {step.render_user()[:200]}...")
            lines.append("")
        return "\n".join(lines)

    def execute(self) -> str:
        """Run the plan through the local Ollama agent."""
        if self._agent is None:
            raise RuntimeError("No agent attached to this plan — use PromptOptimizer.optimize(run_local=True)")
        results: list[str] = []
        for step in self.steps:
            result = self._agent.chat(
                step.render_user(),
                system=step.system,
                stream=True,
                print_stream=True,
            )
            results.append(result)
        return results[-1] if results else ""


# ── optimizer ─────────────────────────────────────────────────────────────────

class PromptOptimizer(OllamaAgent):
    """
    Multi-agent prompt efficiency pipeline.

    Classifies the task, routes to the optimal model configuration,
    injects relevant knowledge, and returns an executable PromptPlan.
    """

    MODEL = "gemma3:4b"
    TEMPERATURE = 0.2

    def __init__(
        self,
        vault_dir: Optional[Path] = None,
        domain_context: str = "",
        run_local: bool = False,
        model: str | None = None,
    ) -> None:
        super().__init__(model=model)
        self.vault_dir = Path(vault_dir) if vault_dir else None
        self.domain_context = domain_context
        self.run_local = run_local

    def classify_task(self, prompt: str) -> str:
        """Heuristic task classification from keywords. Fast — no LLM call."""
        prompt_lower = prompt.lower()
        scores: dict[str, int] = {}
        for task_type, keywords in TASK_KEYWORDS.items():
            scores[task_type] = sum(1 for kw in keywords if kw in prompt_lower)
        best = max(scores, key=lambda t: scores[t])
        return best if scores[best] > 0 else "ask"

    def classify_task_llm(self, prompt: str) -> str:
        """LLM-powered task classification (slower but more accurate)."""
        types = ", ".join(TASK_ROUTING.keys())
        user = (
            f"Classify this task into one of: {types}\n\n"
            f"Task: {prompt}\n\n"
            "Reply with the single task type word only."
        )
        result = self.chat(user, system="You are a task classifier. Reply with one word only.", stream=False, print_stream=False)
        result = result.strip().lower().split()[0] if result.strip() else "ask"
        return result if result in TASK_ROUTING else "ask"

    def compress_context(self, text: str, max_tokens: int = 400) -> str:
        """Compress a long context block into key facts only."""
        if len(text) < max_tokens * 4:
            return text
        route = TASK_ROUTING["compress"]
        compressed = self.chat(
            f"Compress to <{max_tokens} tokens of key facts:\n\n{text}",
            system=route["prefix"],
            stream=False,
            print_stream=False,
        )
        return compressed

    def inject_knowledge(self, prompt: str) -> list[str]:
        """Search the vault and return relevant snippets."""
        if not self.vault_dir:
            return []
        return _search_vault(prompt, self.vault_dir, max_results=3)

    def decompose_task(self, prompt: str, task_type: str) -> list[str]:
        """Break a complex task into subtasks. Returns list of step descriptions."""
        if task_type in ("ask", "explain", "compress"):
            return [prompt]

        decompose_prompt = (
            f"Break this {task_type} task into ≤4 sequential subtasks.\n"
            f"Task: {prompt}\n\n"
            "Return a numbered list only. Each item: one sentence describing exactly what to do."
        )
        result = self.chat(
            decompose_prompt,
            system="You are a task planner. Return a numbered list only.",
            stream=False,
            print_stream=False,
        )
        steps = [
            re.sub(r"^\d+[\.\)]\s*", "", line).strip()
            for line in result.splitlines()
            if re.match(r"^\d", line.strip())
        ]
        return steps if steps else [prompt]

    def optimize(
        self,
        raw_prompt: str,
        *,
        use_llm_classify: bool = False,
        decompose: bool = False,
        compress_vault: bool = False,
        domain_override: str | None = None,
    ) -> PromptPlan:
        """
        Full prompt optimization pipeline.

        Args:
            raw_prompt:        The raw user prompt.
            use_llm_classify:  Use LLM for classification instead of heuristic.
            decompose:         Break into subtasks (costs one LLM call).
            compress_vault:    Compress long vault snippets before injecting.
            domain_override:   Override domain context for this prompt.

        Returns:
            PromptPlan — render() to inspect, execute() to run locally.
        """
        # 1. Classify
        task_type = self.classify_task_llm(raw_prompt) if use_llm_classify else self.classify_task(raw_prompt)
        routing = TASK_ROUTING.get(task_type, TASK_ROUTING["ask"])

        # 2. Knowledge injection
        vault_snippets = self.inject_knowledge(raw_prompt)
        if compress_vault:
            vault_snippets = [self.compress_context(s) for s in vault_snippets]

        # 3. Build system prompt
        domain = domain_override or self.domain_context
        system = routing["prefix"]
        if domain:
            system = f"{system}\n\nDomain context: {domain}"

        # 4. Decompose or single step
        if decompose and task_type in ("implement", "plan", "research"):
            subtasks = self.decompose_task(raw_prompt, task_type)
        else:
            subtasks = [raw_prompt]

        steps = [
            PromptStep(
                task_type=task_type,
                system=system,
                user=subtask,
                model=routing["model"],
                temperature=routing["temperature"],
                context_snippets=vault_snippets if i == 0 else [],
            )
            for i, subtask in enumerate(subtasks)
        ]

        plan = PromptPlan(
            raw_prompt=raw_prompt,
            task_type=task_type,
            steps=steps,
            routing=routing,
            vault_snippets=vault_snippets,
            _agent=self if self.run_local else None,
        )
        return plan

    def quick(self, prompt: str) -> str:
        """Optimize and immediately execute a prompt. Convenience shortcut."""
        plan = self.optimize(prompt)
        if self.vault_dir:
            step = plan.steps[0]
            return self.chat(step.render_user(), system=step.system)
        return self.chat(prompt)
