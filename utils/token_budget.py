"""
token_budget.py — Context window budget management.

Assembles LLM context from multiple sources (system prompt, vault snippets,
code, conversation history) while staying under a token budget.
Uses character-based estimation (fallback) or tiktoken (if installed).

Usage:
    budget = TokenBudget(model="gemma3:4b")
    budget.add(ContextBlock(content=system_prompt, priority=Priority.CRITICAL, label="system"))
    budget.add(ContextBlock(content=file_content, priority=Priority.HIGH, label="main_file"))
    budget.add(ContextBlock(content=vault_note, priority=Priority.MEDIUM, label="context"))

    assembled = budget.assemble()
    print(f"Using {budget.used_tokens}/{budget.max_tokens} tokens")
"""
from __future__ import annotations

import enum
import hashlib
from dataclasses import dataclass, field
from typing import Optional


# ── model context limits ───────────────────────────────────────────────────────

MODEL_LIMITS: dict[str, int] = {
    "gemma3:4b":     131072,
    "gemma3:12b":    131072,
    "qwen2.5:7b":    131072,
    "mistral:7b":    32768,
    "llama3.2:3b":   131072,
    "phi3:mini":     128000,
    "deepseek-r1:7b":131072,
    "default":       8192,
}

# Reserve headroom for response generation
RESPONSE_RESERVE: dict[str, int] = {
    "implement": 4096,
    "review":    2048,
    "plan":      3072,
    "ask":       1024,
    "default":   2048,
}

CHARS_PER_TOKEN = 3.5  # conservative estimate for mixed code+prose


class Priority(enum.IntEnum):
    CRITICAL = 5   # system prompt, task instruction — never dropped
    HIGH     = 4   # the file/code being worked on
    MEDIUM   = 3   # relevant vault context, related code
    LOW      = 2   # conversation history, background
    OPTIONAL = 1   # nice-to-have snippets


@dataclass
class ContextBlock:
    content: str
    priority: Priority = Priority.MEDIUM
    label: str = ""
    truncatable: bool = True     # if False, include whole or drop
    max_chars: Optional[int] = None   # hard cap on this block

    def __post_init__(self):
        if self.max_chars:
            self.content = self.content[:self.max_chars]

    @property
    def estimated_tokens(self) -> int:
        return max(1, int(len(self.content) / CHARS_PER_TOKEN))

    def truncate_to_tokens(self, max_tokens: int) -> "ContextBlock":
        max_chars = int(max_tokens * CHARS_PER_TOKEN)
        if len(self.content) <= max_chars:
            return self
        truncated = self.content[:max_chars]
        last_newline = truncated.rfind("\n")
        if last_newline > max_chars // 2:
            truncated = truncated[:last_newline]
        return ContextBlock(
            content=truncated + f"\n... [truncated {len(self.content) - len(truncated)} chars]",
            priority=self.priority,
            label=self.label,
            truncatable=False,
        )


# ── token budget ───────────────────────────────────────────────────────────────

class TokenBudget:
    """
    Assembles multi-source LLM context within a token budget.

    Blocks are sorted by priority. CRITICAL blocks are always included.
    Lower priority blocks are truncated or dropped to fit the budget.
    """

    def __init__(
        self,
        model: str = "gemma3:4b",
        task_type: str = "default",
        headroom_override: Optional[int] = None,
    ) -> None:
        self.model = model
        self.max_tokens = MODEL_LIMITS.get(model, MODEL_LIMITS["default"])
        reserve = headroom_override or RESPONSE_RESERVE.get(task_type, RESPONSE_RESERVE["default"])
        self.usable_tokens = self.max_tokens - reserve
        self._blocks: list[ContextBlock] = []
        self.used_tokens: int = 0

    def add(self, block: ContextBlock) -> "TokenBudget":
        self._blocks.append(block)
        return self

    def add_many(self, blocks: list[ContextBlock]) -> "TokenBudget":
        self._blocks.extend(blocks)
        return self

    def assemble(self, separator: str = "\n\n---\n\n") -> str:
        """Assemble blocks by priority, truncating/dropping to fit budget."""
        sorted_blocks = sorted(self._blocks, key=lambda b: -b.priority.value)
        chosen: list[ContextBlock] = []
        remaining_tokens = self.usable_tokens

        for block in sorted_blocks:
            tok = block.estimated_tokens
            if tok <= remaining_tokens:
                chosen.append(block)
                remaining_tokens -= tok
            elif block.priority >= Priority.HIGH and block.truncatable:
                truncated = block.truncate_to_tokens(remaining_tokens - 10)
                chosen.append(truncated)
                remaining_tokens = 0
                break
            elif block.priority == Priority.CRITICAL:
                truncated = block.truncate_to_tokens(max(100, remaining_tokens - 10))
                chosen.append(truncated)
                remaining_tokens = 0
                break

        # Re-sort chosen back to logical order (CRITICAL first, then HIGH, etc.)
        chosen.sort(key=lambda b: -b.priority.value)
        self.used_tokens = sum(b.estimated_tokens for b in chosen)

        parts = []
        for block in chosen:
            label_line = f"[{block.label}]\n" if block.label else ""
            parts.append(label_line + block.content)

        return separator.join(parts)

    def budget_report(self) -> dict:
        return {
            "model": self.model,
            "max_tokens": self.max_tokens,
            "usable_tokens": self.usable_tokens,
            "used_tokens": self.used_tokens,
            "utilization_pct": round(100 * self.used_tokens / self.usable_tokens, 1),
            "blocks": len(self._blocks),
        }

    @staticmethod
    def estimate_tokens(text: str) -> int:
        try:
            import tiktoken
            enc = tiktoken.get_encoding("cl100k_base")
            return len(enc.encode(text))
        except ImportError:
            return max(1, int(len(text) / CHARS_PER_TOKEN))

    @staticmethod
    def fits_in_model(text: str, model: str = "gemma3:4b") -> bool:
        limit = MODEL_LIMITS.get(model, MODEL_LIMITS["default"])
        return TokenBudget.estimate_tokens(text) < limit * 0.9

    @classmethod
    def for_code_review(cls, code: str, context: str = "", model: str = "gemma3:4b") -> "TokenBudget":
        """Convenience factory for code review context."""
        budget = cls(model=model, task_type="review")
        budget.add(ContextBlock(code, Priority.HIGH, "code_to_review"))
        if context:
            budget.add(ContextBlock(context, Priority.MEDIUM, "context"))
        return budget

    @classmethod
    def for_implementation(cls, plan: str, repo_map: str = "", vault_context: str = "", model: str = "gemma3:4b") -> "TokenBudget":
        """Convenience factory for implementation tasks."""
        budget = cls(model=model, task_type="implement")
        budget.add(ContextBlock(plan, Priority.CRITICAL, "plan"))
        if repo_map:
            budget.add(ContextBlock(repo_map, Priority.HIGH, "repo_map"))
        if vault_context:
            budget.add(ContextBlock(vault_context, Priority.MEDIUM, "vault_context"))
        return budget
