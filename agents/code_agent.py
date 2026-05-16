"""
code_agent.py — Codebase-aware Ollama agent for implementation and review.

Reads CLAUDE.md, REPO_MAP.md, and KNOWN_BUGS.md from a project root before
running implement or review tasks. Matches the multi-agent role-separation
pattern from GNN-PCNA's CLAUDE.md.

Usage:
    agent = CodeAgent(project_root=Path("C:/Users/advay/GNN_PNCA"))

    # Implement from plan file
    code = agent.implement(plan_path=Path("docs/plans/2026-05-15_parse_pdb.md"))

    # Review a changed file
    issues = agent.review(file_path=Path("src/data_processing/parse_pdb.py"))

    # Ask a question with project context
    answer = agent.ask("What is the expected tensor shape from build_graph_v2?")

    # Generate plan file
    plan = agent.plan("Implement the graph_construction module for PCNA homotrimer")
"""
from __future__ import annotations

import re
from pathlib import Path
from typing import Optional

from .base_agent import OllamaAgent


class CodeAgent(OllamaAgent):
    """
    Project-aware code implementation and review agent.

    Loads project context files automatically before each task.
    Designed for the Claude=plan / Gemma=implement / ChatGPT=review workflow.
    """

    MODEL = "gemma3:4b"
    TEMPERATURE = 0.2
    MAX_TOKENS = 4096

    SYSTEM_IMPLEMENT = """\
You are a senior software engineer implementing code from a detailed plan.

Rules:
- Full type hints on all public functions
- No placeholder TODOs — implement completely
- Do NOT change existing function signatures unless the plan explicitly says to
- Return the complete implemented file, then a one-paragraph change summary
- If the plan specifies a known bug to fix, fix it exactly as described
"""

    SYSTEM_REVIEW = """\
You are a code reviewer performing a critical technical review.

Return a numbered list of issues ONLY (severity: critical | warning | suggestion).
For each issue: file:line_number, description, minimal fix.

Do NOT:
- Suggest redesigns or new features
- Repeat what the code does correctly
- Write any code blocks (just describe the fix)
"""

    SYSTEM_PLAN = """\
You are a software architect creating an implementation plan.

Output a markdown plan file with these sections:
## Goal
## Brain files to read first
## Files to inspect
## Inputs / Outputs
## Step-by-step implementation (numbered)
## Risks and edge cases
## Tests / validation

Do NOT write code. Write the plan only.
At the end, add:
=== GEMINI TASK ===
[copy-pasteable prompt for Gemini to implement from this plan]
"""

    SYSTEM_ASK = """\
You are a senior engineer and computational scientist.
Answer concisely. Use bullet points and code blocks where helpful.
"""

    # Context files to load (in order)
    CONTEXT_FILES = [
        "CLAUDE.md",
        "REPO_MAP.md",
        "KNOWN_BUGS.md",
        "AGENTS.md",
    ]

    def __init__(
        self,
        project_root: Optional[Path] = None,
        model: str | None = None,
        max_context_chars: int = 8000,
    ) -> None:
        super().__init__(model=model)
        self.project_root = Path(project_root) if project_root else Path.cwd()
        self.max_context_chars = max_context_chars
        self._context_cache: Optional[str] = None

    # ── context loading ───────────────────────────────────────────────────────

    def _load_project_context(self, force_reload: bool = False) -> str:
        if self._context_cache and not force_reload:
            return self._context_cache

        sections: list[str] = []
        for fname in self.CONTEXT_FILES:
            fpath = self.project_root / fname
            if fpath.exists():
                text = fpath.read_text(encoding="utf-8", errors="ignore")
                # Trim very long files
                if len(text) > 3000:
                    text = text[:2800] + f"\n\n[... {fname} truncated ...]"
                sections.append(f"=== {fname} ===\n{text}")

        context = "\n\n".join(sections)
        if len(context) > self.max_context_chars:
            context = context[:self.max_context_chars] + "\n\n[... context truncated ...]"

        self._context_cache = context
        return context

    def _load_file(self, path: Path, max_chars: int = 6000) -> str:
        if not path.exists():
            return f"[File not found: {path}]"
        text = path.read_text(encoding="utf-8", errors="ignore")
        if len(text) > max_chars:
            text = text[:max_chars] + f"\n\n[... {path.name} truncated ...]"
        return text

    def _extract_stub_path(self, plan_text: str) -> Optional[Path]:
        """Try to extract the stub file path from a plan file."""
        for line in plan_text.splitlines():
            if "File to implement:" in line or "File:" in line:
                parts = line.split(":", 1)
                if len(parts) == 2:
                    candidate = parts[1].strip()
                    if candidate.startswith("src/") or candidate.startswith("agents/"):
                        return self.project_root / candidate
        return None

    # ── task methods ──────────────────────────────────────────────────────────

    def implement(
        self,
        plan_path: Path,
        *,
        include_project_context: bool = True,
        stream: bool = True,
    ) -> str:
        """Implement from a plan .md file."""
        plan = self._load_file(plan_path)
        stub = ""
        stub_path = self._extract_stub_path(plan)
        if stub_path and stub_path.exists():
            stub_content = self._load_file(stub_path, max_chars=4000)
            stub = f"\n\nCurrent stub to implement:\n```python\n{stub_content}\n```"

        context = self._load_project_context() if include_project_context else ""
        user = (
            (f"=== PROJECT CONTEXT ===\n{context}\n\n" if context else "")
            + f"Plan file:\n\n{plan}{stub}\n\nImplement the file described above."
        )
        return self.chat(user, system=self.SYSTEM_IMPLEMENT, stream=stream)

    def review(
        self,
        file_path: Path,
        *,
        include_known_bugs: bool = True,
        include_project_context: bool = False,
        stream: bool = True,
    ) -> str:
        """Review a source file for issues."""
        code = self._load_file(file_path)
        known_bugs = ""
        if include_known_bugs:
            bugs_path = self.project_root / "KNOWN_BUGS.md"
            if bugs_path.exists():
                known_bugs = f"\nKnown bugs (check these first):\n{self._load_file(bugs_path, 2000)}"

        context = self._load_project_context() if include_project_context else ""
        user = (
            (f"=== PROJECT CONTEXT ===\n{context}\n\n" if context else "")
            + f"File to review: {file_path.name}\n\n```python\n{code}\n```{known_bugs}"
        )
        return self.chat(user, system=self.SYSTEM_REVIEW, stream=stream)

    def ask(
        self,
        question: str,
        *,
        include_project_context: bool = True,
        stream: bool = True,
    ) -> str:
        """Ask a free-form question with project context."""
        context = self._load_project_context() if include_project_context else ""
        user = (
            (f"Project context:\n{context}\n\nQuestion: " if context else "")
            + question
        )
        return self.chat(user, system=self.SYSTEM_ASK, stream=stream)

    def plan(
        self,
        task: str,
        *,
        output_path: Optional[Path] = None,
        stream: bool = True,
    ) -> str:
        """Generate an implementation plan. Optionally write to docs/plans/."""
        from datetime import datetime
        context = self._load_project_context()
        user = (
            f"=== PROJECT CONTEXT ===\n{context}\n\n"
            f"Create an implementation plan for this task:\n\n{task}"
        )
        result = self.chat(user, system=self.SYSTEM_PLAN, stream=stream)

        if output_path is None:
            plans_dir = self.project_root / "docs" / "plans"
            slug = re.sub(r"[^\w\s-]", "", task.lower())[:40].strip().replace(" ", "_")
            date_str = datetime.now().strftime("%Y-%m-%d")
            output_path = plans_dir / f"{date_str}_{slug}.md"

        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(result, encoding="utf-8")
        print(f"\n[code_agent] Plan written: {output_path}")
        return result

    def diff_review(
        self,
        diff_text: str,
        *,
        stream: bool = True,
    ) -> str:
        """Review a git diff output for issues."""
        system = (
            self.SYSTEM_REVIEW
            + "\n\nYou are reviewing a git diff. Focus on: logic errors, data leakage, "
            "off-by-one errors, missing edge cases, incorrect API usage."
        )
        user = f"Git diff to review:\n\n```diff\n{diff_text}\n```"
        return self.chat(user, system=system, stream=stream)

    def reload_context(self) -> None:
        """Force reload of project context files."""
        self._context_cache = None
        self._load_project_context()
        print(f"[code_agent] Context reloaded from {self.project_root}")
