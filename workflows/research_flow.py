"""
research_flow.py — Interactive research workflow: YouTube → NotebookLM → Vault.

Usage:
    python workflows/research_flow.py "PCNA cryptic pocket GNN" --n 6
    python workflows/research_flow.py "protein folding" --artifacts report flashcards mindmap
    python workflows/research_flow.py "AlphaFold" --vault C:/Users/advay/Obsidian/Research
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(REPO_ROOT))

from agents.research_pipeline import ResearchPipeline, ARTIFACT_TYPES


def main() -> None:
    parser = argparse.ArgumentParser(description="YouTube → NotebookLM research pipeline")
    parser.add_argument("topic", help="Research topic to search")
    parser.add_argument("--n", type=int, default=5, help="Number of YouTube videos (default 5)")
    parser.add_argument("--artifacts", nargs="+", default=["report"],
                        choices=ARTIFACT_TYPES, help="NotebookLM artifact types")
    parser.add_argument("--question", default="", help="Focus question for artifacts")
    parser.add_argument("--vault", default="", help="Obsidian vault directory for notes")
    parser.add_argument("--title", default="", help="Notebook title (default: 'Research: <topic>')")
    parser.add_argument("--yt-script", help="Path to yt_research.py")
    parser.add_argument("--nlm-script", help="Path to notebooklm_skill.py")
    args = parser.parse_args()

    vault = Path(args.vault) if args.vault else None
    pipeline = ResearchPipeline(
        vault_dir=vault,
        yt_script=Path(args.yt_script) if args.yt_script else None,
        nlm_script=Path(args.nlm_script) if args.nlm_script else None,
    )

    result = pipeline.run(
        topic=args.topic,
        n_videos=args.n,
        artifact_types=args.artifacts,
        focus_question=args.question,
        notebook_title=args.title or f"Research: {args.topic}",
    )

    print(f"\n=== RESEARCH COMPLETE ===")
    print(f"Topic:      {result.topic}")
    print(f"Videos:     {len(result.videos)}")
    print(f"Notebook:   {result.notebook_id}")
    print(f"Artifacts:  {list(result.artifacts.keys())}")
    if result.vault_notes:
        print(f"Vault:      {result.vault_notes[0]}")


if __name__ == "__main__":
    main()
