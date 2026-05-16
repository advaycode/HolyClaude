"""
overnight_agent.py — Background task scheduler + morning briefing.

Runs a list of tasks while you sleep, collects results, and produces
a consolidated morning briefing via Ollama.

Usage:
    agent = OvernightAgent(vault_dir=Path("C:/Users/advay/Obsidian"))

    # Register tasks
    agent.add_task("research", topic="graph neural networks protein pockets", n_videos=5)
    agent.add_task("study", subject="ap-physics", artifact="video")
    agent.add_task("crawl", topic="PCNA cryptic pockets", keywords=["PCNA", "GNN"])

    # Run overnight
    agent.run()         # blocks until all tasks done
    agent.run_async()   # fire and forget (subprocess)

    # CLI
    python agents/overnight_agent.py --tasks tasks.json
    python agents/overnight_agent.py --research "protein folding" --study ap-physics
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
import threading
import time
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

from .base_agent import OllamaAgent


# ── task definitions ──────────────────────────────────────────────────────────

@dataclass
class OvernightTask:
    task_type: str          # "research" | "study" | "crawl" | "script" | "prompt"
    label: str = ""
    params: dict = field(default_factory=dict)
    result: Any = None
    error: str = ""
    elapsed: float = 0.0
    status: str = "pending"   # pending | running | done | failed


@dataclass
class OvernightReport:
    started_at: str
    finished_at: str = ""
    tasks: list[OvernightTask] = field(default_factory=list)
    briefing: str = ""
    total_elapsed: float = 0.0

    def to_dict(self) -> dict:
        return {
            "started_at": self.started_at,
            "finished_at": self.finished_at,
            "total_elapsed": round(self.total_elapsed, 1),
            "tasks": [
                {
                    "label": t.label or t.task_type,
                    "status": t.status,
                    "elapsed": round(t.elapsed, 1),
                    "error": t.error,
                    "result_summary": str(t.result)[:200] if t.result else "",
                }
                for t in self.tasks
            ],
            "briefing": self.briefing,
        }


# ── task runners ──────────────────────────────────────────────────────────────

def _run_research(params: dict) -> str:
    from .research_pipeline import ResearchPipeline
    pipeline = ResearchPipeline(
        vault_dir=Path(params["vault_dir"]) if params.get("vault_dir") else None
    )
    result = pipeline.run(
        topic=params["topic"],
        n_videos=params.get("n_videos", 5),
        artifact_types=params.get("artifact_types", ["report"]),
    )
    return f"Research done: {len(result.videos)} videos, {list(result.artifacts.keys())}"


def _run_study(params: dict) -> str:
    from .study_agent import StudyAgent
    subjects = {"ap-physics": StudyAgent.ap_physics, "ap-stats": StudyAgent.ap_stats}
    subject = params.get("subject", "ap-physics")
    builder = subjects.get(subject, StudyAgent.ap_physics)
    agent = builder()
    result = agent.run_daily(
        n_videos=params.get("n_videos", 4),
        artifact=params.get("artifact", "video"),
        force_topic=params.get("force_topic"),
    )
    return f"Study done: {result.get('topic', '?')}"


def _run_crawl(params: dict) -> str:
    from .crawler_agent import CrawlerAgent, PubMedSource, ArXivSource
    output_dir = Path(params.get("output_dir", "data/overnight"))
    crawler = CrawlerAgent(
        topic=params["topic"],
        keywords=params.get("keywords", params["topic"].split()),
        output_dir=output_dir,
        workers=params.get("workers", 4),
    )
    if params.get("sources_pubmed"):
        crawler.add_source(PubMedSource(queries=[params["topic"]]))
    if params.get("sources_arxiv", True):
        crawler.add_source(ArXivSource(query=params["topic"]))
    catalog = crawler.run()
    passed = catalog.get("stats", {}).get("passed", 0)
    return f"Crawl done: {passed} records passed"


def _run_script(params: dict) -> str:
    """Run an arbitrary Python script or shell command."""
    cmd = params.get("cmd", [])
    if isinstance(cmd, str):
        cmd = cmd.split()
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=params.get("timeout", 300))
    if result.returncode != 0:
        raise RuntimeError(result.stderr[:500])
    return result.stdout.strip()[:500]


def _run_prompt(params: dict) -> str:
    """Run a prompt through the local Ollama agent."""
    from .prompt_optimizer import PromptOptimizer
    optimizer = PromptOptimizer(
        vault_dir=Path(params["vault_dir"]) if params.get("vault_dir") else None,
        run_local=True,
    )
    return optimizer.quick(params["prompt"])


TASK_RUNNERS = {
    "research": _run_research,
    "study": _run_study,
    "crawl": _run_crawl,
    "script": _run_script,
    "prompt": _run_prompt,
}


# ── overnight agent ───────────────────────────────────────────────────────────

class OvernightAgent(OllamaAgent):
    """
    Background task scheduler with morning briefing.

    Add tasks, run them sequentially or threaded, get an Ollama-generated
    summary as a morning briefing in your vault.
    """

    MODEL = "gemma3:4b"
    TEMPERATURE = 0.3

    BRIEFING_SYSTEM = """\
You are generating a morning briefing for a high school student and builder.
Summarize what was accomplished overnight: research found, study completed, data collected.
Keep it concise, scannable, and actionable. Use bullet points. Under 400 words.
"""

    def __init__(
        self,
        vault_dir: Optional[Path] = None,
        output_dir: Optional[Path] = None,
        model: str | None = None,
    ) -> None:
        super().__init__(model=model)
        self.vault_dir = Path(vault_dir) if vault_dir else None
        self.output_dir = Path(output_dir or Path.home() / "HolyClaude" / "data" / "overnight")
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self._tasks: list[OvernightTask] = []

    def add_task(self, task_type: str, label: str = "", **params) -> None:
        if task_type not in TASK_RUNNERS:
            raise ValueError(f"Unknown task type: {task_type}. Choose: {list(TASK_RUNNERS)}")
        if self.vault_dir and "vault_dir" not in params:
            params["vault_dir"] = str(self.vault_dir)
        self._tasks.append(OvernightTask(
            task_type=task_type,
            label=label or f"{task_type}: {list(params.values())[:1]}",
            params=params,
        ))

    def add_research(self, topic: str, n_videos: int = 5, **kw) -> None:
        self.add_task("research", label=f"Research: {topic}", topic=topic, n_videos=n_videos, **kw)

    def add_study(self, subject: str = "ap-physics", artifact: str = "video", **kw) -> None:
        self.add_task("study", label=f"Study: {subject}", subject=subject, artifact=artifact, **kw)

    def add_crawl(self, topic: str, keywords: list[str] | None = None, **kw) -> None:
        self.add_task("crawl", label=f"Crawl: {topic}", topic=topic, keywords=keywords or topic.split(), **kw)

    def add_script(self, cmd: str | list[str], label: str = "", **kw) -> None:
        self.add_task("script", label=label or f"Script: {cmd}", cmd=cmd, **kw)

    def add_prompt(self, prompt: str, label: str = "", **kw) -> None:
        self.add_task("prompt", label=label or f"Prompt: {prompt[:40]}", prompt=prompt, **kw)

    # ── execution ─────────────────────────────────────────────────────────────

    def run(self, parallel: bool = False) -> OvernightReport:
        """Run all tasks and generate morning briefing."""
        report = OvernightReport(started_at=datetime.now(timezone.utc).isoformat())
        report.tasks = self._tasks
        t0 = time.monotonic()

        print(f"\n{'='*60}")
        print(f"  Overnight Agent — {len(self._tasks)} tasks")
        print(f"  Started: {report.started_at[:19]}")
        print(f"{'='*60}\n")

        if parallel:
            threads = []
            for task in self._tasks:
                t = threading.Thread(target=self._execute_task, args=(task,), daemon=True)
                t.start()
                threads.append(t)
            for t in threads:
                t.join()
        else:
            for task in self._tasks:
                self._execute_task(task)

        report.finished_at = datetime.now(timezone.utc).isoformat()
        report.total_elapsed = time.monotonic() - t0

        # Generate briefing
        print("\n[overnight] Generating morning briefing...")
        report.briefing = self._generate_briefing(report)

        # Save report
        self._save_report(report)

        print(f"\n{'='*60}")
        print(f"  Overnight complete — {report.total_elapsed:.0f}s")
        print(f"  Done: {sum(1 for t in self._tasks if t.status == 'done')}/{len(self._tasks)}")
        print(f"{'='*60}")
        print(f"\n=== MORNING BRIEFING ===\n{report.briefing}")

        return report

    def _execute_task(self, task: OvernightTask) -> None:
        task.status = "running"
        t0 = time.monotonic()
        print(f"\n[overnight] Starting: {task.label}")
        try:
            runner = TASK_RUNNERS[task.task_type]
            task.result = runner(task.params)
            task.status = "done"
            print(f"[overnight] Done: {task.label} ({time.monotonic() - t0:.1f}s)")
        except Exception as e:
            task.error = str(e)
            task.status = "failed"
            print(f"[overnight] FAILED: {task.label} — {e}")
        task.elapsed = time.monotonic() - t0

    def _generate_briefing(self, report: OvernightReport) -> str:
        if not self.health_check():
            return self._fallback_briefing(report)

        summary_lines = [
            f"Overnight tasks completed at {report.finished_at[:19]}.",
            f"Total time: {report.total_elapsed:.0f}s.",
            "",
        ]
        for task in report.tasks:
            status_icon = "OK" if task.status == "done" else "FAIL"
            summary_lines.append(
                f"[{status_icon}] {task.label}: "
                f"{task.result or task.error or 'no output'}"
            )

        prompt = "\n".join(summary_lines)
        return self.chat(prompt, system=self.BRIEFING_SYSTEM, stream=False, print_stream=False)

    @staticmethod
    def _fallback_briefing(report: OvernightReport) -> str:
        lines = [f"Morning Briefing — {report.finished_at[:10]}", ""]
        for task in report.tasks:
            icon = "DONE" if task.status == "done" else "FAIL"
            lines.append(f"- [{icon}] {task.label}: {task.result or task.error or '?'}")
        return "\n".join(lines)

    def _save_report(self, report: OvernightReport) -> None:
        date_str = datetime.now().strftime("%Y-%m-%d")
        out = self.output_dir / f"{date_str}_overnight_report.json"
        out.write_text(json.dumps(report.to_dict(), indent=2), encoding="utf-8")

        if self.vault_dir:
            note = self.vault_dir / "overnight" / f"{date_str}_briefing.md"
            note.parent.mkdir(parents=True, exist_ok=True)
            note.write_text(
                f"---\ntype: overnight-briefing\ndate: {date_str}\n---\n\n"
                f"# Morning Briefing — {date_str}\n\n"
                + report.briefing + "\n\n"
                + "## Task Log\n\n"
                + "\n".join(
                    f"- **{t.label}**: {t.status} ({t.elapsed:.1f}s)"
                    for t in report.tasks
                ),
                encoding="utf-8",
            )
            print(f"[overnight] Vault note: {note}")

    def load_tasks_from_json(self, path: Path) -> None:
        """Load tasks from a JSON file. Useful for scheduling."""
        tasks_data = json.loads(Path(path).read_text(encoding="utf-8"))
        for t in tasks_data:
            self.add_task(t.pop("task_type"), t.pop("label", ""), **t)


def main() -> None:
    parser = argparse.ArgumentParser(description="Overnight agent — run tasks and generate briefing")
    parser.add_argument("--research", nargs="+", metavar="TOPIC", help="Research topic(s)")
    parser.add_argument("--study", default="", help="Study subject (ap-physics, ap-stats)")
    parser.add_argument("--crawl", nargs="+", metavar="TOPIC", help="Crawl topic(s)")
    parser.add_argument("--tasks", help="JSON file with task list")
    parser.add_argument("--vault", default="", help="Obsidian vault dir")
    parser.add_argument("--parallel", action="store_true", help="Run tasks in parallel threads")
    args = parser.parse_args()

    vault = Path(args.vault) if args.vault else None
    agent = OvernightAgent(vault_dir=vault)

    if args.tasks:
        agent.load_tasks_from_json(Path(args.tasks))
    if args.research:
        for topic in args.research:
            agent.add_research(topic)
    if args.study:
        agent.add_study(subject=args.study)
    if args.crawl:
        for topic in args.crawl:
            agent.add_crawl(topic)

    if not agent._tasks:
        print("No tasks specified. Use --research, --study, --crawl, or --tasks.")
        sys.exit(1)

    agent.run(parallel=args.parallel)


if __name__ == "__main__":
    main()
