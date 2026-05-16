"""
research_pipeline.py — YouTube → NotebookLM → Knowledge Graph pipeline.

Chains yt-research (yt-dlp) → NotebookLM artifact generation → Obsidian vault write.

Usage:
    pipeline = ResearchPipeline(vault_dir=Path("docs/research"))
    result = pipeline.run("PCNA cryptic pocket graph neural network", n_videos=5)

    # Or step by step:
    videos = pipeline.search_youtube("protein pocket prediction GNN", n=8)
    notebook = pipeline.send_to_notebooklm(videos, title="GNN Pocket Research")
    notes = pipeline.generate_artifacts(notebook, types=["summary", "flashcards"])
"""
from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional


# ── data types ────────────────────────────────────────────────────────────────

@dataclass
class VideoResult:
    title: str
    url: str
    channel: str = ""
    duration: str = ""
    views: int = 0
    description: str = ""


@dataclass
class ResearchResult:
    topic: str
    videos: list[VideoResult] = field(default_factory=list)
    notebook_id: str = ""
    artifacts: dict[str, str] = field(default_factory=dict)
    vault_notes: list[Path] = field(default_factory=list)
    generated_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


# ── yt-research wrapper ───────────────────────────────────────────────────────

YT_RESEARCH_SCRIPT = Path.home() / "tools" / "yt-research" / "yt_research.py"


def search_youtube(
    query: str,
    n: int = 5,
    format: str = "json",
    script_path: Optional[Path] = None,
) -> list[VideoResult]:
    """
    Search YouTube via yt-dlp (no API key needed).
    Requires ~/tools/yt-research/yt_research.py.
    """
    script = Path(script_path or YT_RESEARCH_SCRIPT)
    if not script.exists():
        raise FileNotFoundError(f"yt-research script not found: {script}")

    cmd = [sys.executable, str(script), query, "-n", str(n), "-f", "json"]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)

    if result.returncode != 0:
        raise RuntimeError(f"yt-research failed: {result.stderr[:300]}")

    try:
        data = json.loads(result.stdout)
        return [
            VideoResult(
                title=v.get("title", ""),
                url=v.get("url", ""),
                channel=v.get("channel", ""),
                duration=str(v.get("duration", "")),
                views=int(v.get("views", 0) or 0),
                description=v.get("description", "")[:300],
            )
            for v in (data if isinstance(data, list) else data.get("results", []))
        ]
    except (json.JSONDecodeError, KeyError) as e:
        raise RuntimeError(f"yt-research JSON parse failed: {e}\nOutput: {result.stdout[:300]}")


# ── notebooklm wrapper ────────────────────────────────────────────────────────

NOTEBOOKLM_SCRIPT = Path.home() / "tools" / "notebooklm" / "notebooklm_skill.py"

ARTIFACT_TYPES = [
    "infographic", "slides", "flashcards", "quiz",
    "audio", "video", "mindmap", "report", "table",
]


def _run_notebooklm(args: list[str], script_path: Optional[Path] = None) -> str:
    script = Path(script_path or NOTEBOOKLM_SCRIPT)
    if not script.exists():
        raise FileNotFoundError(f"notebooklm script not found: {script}")
    cmd = [sys.executable, str(script)] + args
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
    if result.returncode != 0:
        raise RuntimeError(f"notebooklm failed: {result.stderr[:300]}")
    return result.stdout.strip()


def create_notebooklm_notebook(
    title: str,
    sources: list[str],
    script_path: Optional[Path] = None,
) -> str:
    """Create a NotebookLM notebook and add sources. Returns notebook ID."""
    output = _run_notebooklm(["create", "--title", title], script_path)
    # Parse notebook ID from output
    for line in output.splitlines():
        if "id" in line.lower() or "notebook" in line.lower():
            parts = line.split()
            for part in parts:
                if len(part) > 10 and part.replace("-", "").replace("_", "").isalnum():
                    notebook_id = part.strip(":")
                    break

    # Write sources to temp file
    with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False, encoding="utf-8") as f:
        f.write("\n".join(sources))
        sources_file = f.name

    try:
        _run_notebooklm(["add-sources", "--notebook", notebook_id, "--sources-file", sources_file], script_path)
    except Exception:
        pass  # Sources may have been added inline

    return notebook_id


def generate_artifact(
    notebook_id: str,
    artifact_type: str,
    question: str = "",
    script_path: Optional[Path] = None,
) -> str:
    """Generate a NotebookLM artifact. Returns artifact content/path."""
    args = ["artifact", "--notebook", notebook_id, "--type", artifact_type]
    if question:
        args += ["--question", question]
    return _run_notebooklm(args, script_path)


# ── pipeline ──────────────────────────────────────────────────────────────────

class ResearchPipeline:
    """
    Full research pipeline: YouTube → NotebookLM → Obsidian vault.

    Example:
        pipeline = ResearchPipeline(vault_dir=Path("docs/research"))
        result = pipeline.run(
            topic="protein pocket prediction GNN",
            n_videos=6,
            artifact_types=["summary", "flashcards"],
        )
    """

    def __init__(
        self,
        vault_dir: Optional[Path] = None,
        yt_script: Optional[Path] = None,
        nlm_script: Optional[Path] = None,
    ) -> None:
        self.vault_dir = Path(vault_dir) if vault_dir else None
        self.yt_script = yt_script
        self.nlm_script = nlm_script

    def search_youtube(self, query: str, n: int = 5) -> list[VideoResult]:
        print(f"[research] Searching YouTube: {query!r} (n={n})")
        videos = search_youtube(query, n=n, script_path=self.yt_script)
        print(f"[research] Found {len(videos)} videos")
        for v in videos:
            print(f"  - {v.title[:60]} | {v.channel} | {v.url}")
        return videos

    def send_to_notebooklm(
        self,
        videos: list[VideoResult],
        title: str = "Research",
    ) -> str:
        print(f"\n[research] Creating NotebookLM notebook: {title!r}")
        urls = [v.url for v in videos if v.url]
        notebook_id = create_notebooklm_notebook(title, urls, script_path=self.nlm_script)
        print(f"[research] Notebook created: {notebook_id}")
        return notebook_id

    def generate_artifacts(
        self,
        notebook_id: str,
        types: list[str] | None = None,
        focus_question: str = "",
    ) -> dict[str, str]:
        types = types or ["report"]
        artifacts: dict[str, str] = {}
        for atype in types:
            print(f"[research] Generating {atype}...")
            try:
                content = generate_artifact(notebook_id, atype, focus_question, self.nlm_script)
                artifacts[atype] = content
                print(f"[research]   {atype}: {len(content)} chars")
            except Exception as e:
                print(f"[research]   {atype} failed: {e}")
        return artifacts

    def write_to_vault(self, topic: str, videos: list[VideoResult], artifacts: dict[str, str]) -> list[Path]:
        if not self.vault_dir:
            return []
        out_dir = self.vault_dir / "youtube_research"
        out_dir.mkdir(parents=True, exist_ok=True)

        slug = topic.lower().replace(" ", "_")[:40]
        now = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        written: list[Path] = []

        # Main research note
        lines = [
            f"---",
            f"type: research",
            f"topic: {topic}",
            f"date: {now}",
            f"videos: {len(videos)}",
            f"---",
            f"",
            f"# Research: {topic}",
            f"",
            f"## Sources ({len(videos)} videos)",
            "",
        ]
        for v in videos:
            lines.append(f"- [{v.title}]({v.url}) — {v.channel}")
        lines.append("")

        for atype, content in artifacts.items():
            lines += [f"## {atype.title()}", "", content[:2000], ""]

        note_path = out_dir / f"{now}_{slug}.md"
        note_path.write_text("\n".join(lines), encoding="utf-8")
        written.append(note_path)
        print(f"[research] Vault note: {note_path}")
        return written

    def run(
        self,
        topic: str,
        n_videos: int = 5,
        artifact_types: list[str] | None = None,
        focus_question: str = "",
        notebook_title: str | None = None,
    ) -> ResearchResult:
        """End-to-end pipeline: search → notebook → artifacts → vault."""
        result = ResearchResult(topic=topic)

        result.videos = self.search_youtube(topic, n=n_videos)
        if not result.videos:
            print("[research] No videos found — aborting")
            return result

        title = notebook_title or f"Research: {topic}"
        result.notebook_id = self.send_to_notebooklm(result.videos, title=title)

        result.artifacts = self.generate_artifacts(
            result.notebook_id,
            types=artifact_types or ["report"],
            focus_question=focus_question,
        )

        result.vault_notes = self.write_to_vault(topic, result.videos, result.artifacts)

        print(f"\n[research] Done: {len(result.videos)} videos, {len(result.artifacts)} artifacts, {len(result.vault_notes)} notes")
        return result
