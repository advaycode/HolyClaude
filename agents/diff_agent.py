"""
diff_agent.py — Git-aware code reviewer via Ollama.

Parses `git diff` output into hunks, runs per-file and per-hunk Ollama review,
scores severity, and generates a PR summary.

Usage:
    agent = DiffAgent(project_root=Path("C:/Users/advay/GNN_PNCA"))
    agent.review_staged()          # review staged changes
    agent.review_branch("main")    # review all changes vs main

    # CLI:
    python agents/diff_agent.py --branch main --project C:/Users/advay/GNN_PNCA
    python agents/diff_agent.py --staged
"""
from __future__ import annotations

import argparse
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from .base_agent import OllamaAgent


# ── diff structures ───────────────────────────────────────────────────────────

@dataclass
class DiffHunk:
    header: str          # @@ -a,b +c,d @@
    context: str         # surrounding code context
    removed: list[str] = field(default_factory=list)
    added: list[str] = field(default_factory=list)

    def render(self) -> str:
        lines = [self.header]
        lines += [f"-{l}" for l in self.removed]
        lines += [f"+{l}" for l in self.added]
        return "\n".join(lines)


@dataclass
class FileDiff:
    path: str
    hunks: list[DiffHunk]
    additions: int = 0
    deletions: int = 0
    is_new: bool = False
    is_deleted: bool = False
    language: str = ""

    def render(self) -> str:
        return f"--- {self.path}\n+++ {self.path}\n" + "\n".join(h.render() for h in self.hunks)


@dataclass
class ReviewResult:
    path: str
    severity: str          # critical | warning | info | ok
    issues: list[str]
    suggestions: list[str]
    summary: str
    hunk_reviews: list[str] = field(default_factory=list)

    def render(self) -> str:
        lines = [f"## {self.path}  [{self.severity.upper()}]", "", self.summary, ""]
        if self.issues:
            lines += ["**Issues:**"] + [f"- {i}" for i in self.issues] + [""]
        if self.suggestions:
            lines += ["**Suggestions:**"] + [f"- {s}" for s in self.suggestions] + [""]
        return "\n".join(lines)


# ── diff parser ───────────────────────────────────────────────────────────────

def _detect_language(path: str) -> str:
    ext = Path(path).suffix.lower()
    return {".py": "python", ".ts": "typescript", ".tsx": "tsx", ".js": "javascript",
            ".rs": "rust", ".go": "go", ".java": "java", ".cpp": "cpp", ".c": "c",
            ".md": "markdown", ".json": "json", ".yaml": "yaml", ".yml": "yaml"}.get(ext, "")


def parse_diff(raw: str) -> list[FileDiff]:
    files: list[FileDiff] = []
    current_file: Optional[FileDiff] = None
    current_hunk: Optional[DiffHunk] = None

    for line in raw.splitlines():
        if line.startswith("diff --git"):
            if current_hunk and current_file:
                current_file.hunks.append(current_hunk)
                current_hunk = None
            if current_file:
                files.append(current_file)
            path = line.split(" b/", 1)[-1] if " b/" in line else line
            current_file = FileDiff(path=path, hunks=[], language=_detect_language(path))

        elif line.startswith("new file"):
            if current_file:
                current_file.is_new = True
        elif line.startswith("deleted file"):
            if current_file:
                current_file.is_deleted = True

        elif line.startswith("@@") and current_file:
            if current_hunk:
                current_file.hunks.append(current_hunk)
            header = line.split("@@")[1].strip() if "@@" in line else line
            current_hunk = DiffHunk(header=f"@@ {header} @@", context="")

        elif current_hunk is not None:
            if line.startswith("-") and not line.startswith("---"):
                current_hunk.removed.append(line[1:])
                if current_file:
                    current_file.deletions += 1
            elif line.startswith("+") and not line.startswith("+++"):
                current_hunk.added.append(line[1:])
                if current_file:
                    current_file.additions += 1
            else:
                current_hunk.context += line + "\n"

    if current_hunk and current_file:
        current_file.hunks.append(current_hunk)
    if current_file:
        files.append(current_file)

    return files


# ── diff agent ────────────────────────────────────────────────────────────────

class DiffAgent(OllamaAgent):
    """
    Runs Ollama code review on git diffs — per-file and per-hunk.

    Produces severity scores (critical/warning/info/ok), issues list,
    and a PR-ready summary for the whole changeset.
    """

    MODEL = "gemma3:4b"
    TEMPERATURE = 0.2
    MAX_HUNK_CHARS = 2000
    MAX_FILE_CHARS = 4000

    REVIEW_SYSTEM = """\
You are a senior code reviewer. Analyze the diff and respond in this exact format:
SEVERITY: [critical|warning|info|ok]
ISSUES:
- <issue 1>
- <issue 2>
SUGGESTIONS:
- <suggestion 1>
SUMMARY: <one sentence>

Focus on: bugs, security issues, performance, logic errors, missing edge cases.
Do NOT comment on style or formatting. Be concise."""

    PR_SYSTEM = """\
You are writing a PR description. Given a list of file review summaries, write:
## Summary
- <bullet points of what changed>

## Risk
- <what could break>

## Test Plan
- [ ] <test item>

Be concise. Under 200 words total."""

    def __init__(self, project_root: Optional[Path] = None, **kw) -> None:
        super().__init__(**kw)
        self.project_root = Path(project_root) if project_root else Path.cwd()

    # ── git operations ────────────────────────────────────────────────────────

    def _git(self, *args: str) -> str:
        result = subprocess.run(
            ["git", *args],
            capture_output=True, text=True,
            cwd=self.project_root,
        )
        if result.returncode != 0 and result.stderr:
            print(f"[diff] git warning: {result.stderr[:200]}", file=sys.stderr)
        return result.stdout

    def get_staged_diff(self) -> str:
        return self._git("diff", "--cached")

    def get_branch_diff(self, base: str = "main") -> str:
        return self._git("diff", f"{base}...HEAD")

    def get_working_diff(self) -> str:
        return self._git("diff", "HEAD")

    def get_commit_diff(self, sha: str) -> str:
        return self._git("show", sha)

    # ── review ────────────────────────────────────────────────────────────────

    def _parse_review(self, raw: str, path: str) -> ReviewResult:
        severity = "info"
        issues: list[str] = []
        suggestions: list[str] = []
        summary = raw[:200]
        section = None

        for line in raw.splitlines():
            l = line.strip()
            if l.startswith("SEVERITY:"):
                sev = l.split(":", 1)[1].strip().lower()
                if sev in ("critical", "warning", "info", "ok"):
                    severity = sev
            elif l == "ISSUES:":
                section = "issues"
            elif l == "SUGGESTIONS:":
                section = "suggestions"
            elif l.startswith("SUMMARY:"):
                summary = l.split(":", 1)[1].strip()
                section = None
            elif l.startswith("-") and section == "issues":
                issues.append(l[1:].strip())
            elif l.startswith("-") and section == "suggestions":
                suggestions.append(l[1:].strip())

        return ReviewResult(path=path, severity=severity, issues=issues,
                            suggestions=suggestions, summary=summary)

    def review_file(self, file_diff: FileDiff) -> ReviewResult:
        if not self.health_check():
            return ReviewResult(path=file_diff.path, severity="info", issues=[],
                                suggestions=[], summary="Ollama offline — skipped")

        diff_text = file_diff.render()[:self.MAX_FILE_CHARS]
        lang_hint = f"Language: {file_diff.language}\n\n" if file_diff.language else ""
        prompt = f"{lang_hint}File: {file_diff.path}\n\n```diff\n{diff_text}\n```"

        raw = self.chat(prompt, system=self.REVIEW_SYSTEM, stream=False, print_stream=False)
        return self._parse_review(raw, file_diff.path)

    def review_diff(self, raw_diff: str, label: str = "changeset") -> list[ReviewResult]:
        files = parse_diff(raw_diff)
        if not files:
            print(f"[diff] No files to review in {label}", file=sys.stderr)
            return []

        print(f"\n[diff] Reviewing {len(files)} files in {label}...", file=sys.stderr)
        results: list[ReviewResult] = []

        for file_diff in files:
            print(f"  → {file_diff.path} (+{file_diff.additions}/-{file_diff.deletions})", file=sys.stderr)
            result = self.review_file(file_diff)
            results.append(result)
            icon = {"critical": "CRIT", "warning": "WARN", "info": "INFO", "ok": "  OK"}.get(result.severity, "????")
            print(f"    [{icon}] {result.summary[:70]}", file=sys.stderr)

        return results

    def generate_pr_summary(self, results: list[ReviewResult]) -> str:
        if not results:
            return "No changes to summarize."
        summaries = "\n".join(f"- {r.path} [{r.severity}]: {r.summary}" for r in results)
        prompt = f"Review summaries:\n{summaries}"
        return self.chat(prompt, system=self.PR_SYSTEM, stream=False, print_stream=False)

    def print_report(self, results: list[ReviewResult]) -> None:
        severity_order = {"critical": 0, "warning": 1, "info": 2, "ok": 3}
        results_sorted = sorted(results, key=lambda r: severity_order.get(r.severity, 9))

        print(f"\n{'='*65}")
        print(f"  DIFF REVIEW REPORT")
        print(f"{'='*65}")
        for r in results_sorted:
            print(r.render())
        print(f"{'='*65}")

        counts = {sev: sum(1 for r in results if r.severity == sev) for sev in ("critical", "warning", "info", "ok")}
        print(f"  CRITICAL={counts['critical']}  WARNING={counts['warning']}  INFO={counts['info']}  OK={counts['ok']}")
        print(f"{'='*65}")

    # ── convenience ───────────────────────────────────────────────────────────

    def review_staged(self) -> list[ReviewResult]:
        diff = self.get_staged_diff()
        results = self.review_diff(diff, label="staged changes")
        self.print_report(results)
        return results

    def review_branch(self, base: str = "main") -> list[ReviewResult]:
        diff = self.get_branch_diff(base)
        results = self.review_diff(diff, label=f"branch vs {base}")
        self.print_report(results)
        if results:
            print("\n=== PR SUMMARY ===\n")
            print(self.generate_pr_summary(results))
        return results


def main() -> None:
    parser = argparse.ArgumentParser(description="Ollama git diff reviewer")
    parser.add_argument("--staged", action="store_true", help="Review staged changes")
    parser.add_argument("--branch", default="", help="Review vs base branch (e.g. main)")
    parser.add_argument("--commit", default="", help="Review a specific commit SHA")
    parser.add_argument("--project", default=".", help="Project root directory")
    parser.add_argument("--model", default="gemma3:4b")
    args = parser.parse_args()

    agent = DiffAgent(project_root=Path(args.project), model=args.model)
    agent.require_ollama()

    if args.staged:
        agent.review_staged()
    elif args.branch:
        agent.review_branch(args.branch)
    elif args.commit:
        diff = agent.get_commit_diff(args.commit)
        results = agent.review_diff(diff, label=f"commit {args.commit[:8]}")
        agent.print_report(results)
    else:
        diff = agent.get_working_diff()
        results = agent.review_diff(diff, label="working tree")
        agent.print_report(results)


if __name__ == "__main__":
    main()
