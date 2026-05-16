"""
gnn_pipeline.py — End-to-end GNN-PCNA research data pipeline.

Stages:
  1. crawl      — Multi-source crawl (PubMed, ArXiv, Zenodo, RCSB)
  2. verify     — Gemma L6 relevance scoring
  3. vault      — Write Obsidian hub notes
  4. youtube    — YouTube → NotebookLM research pipeline
  5. briefing   — Ollama morning briefing on findings

Usage:
    python workflows/gnn_pipeline.py --topic "PCNA cryptic pocket" --stages crawl verify vault
    python workflows/gnn_pipeline.py --all --vault C:/Users/advay/Obsidian/GNN-PCNA
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(REPO_ROOT))


STAGES = ["crawl", "verify", "vault", "youtube", "briefing"]

GNN_PCNA_QUERIES = {
    "pubmed": [
        "PCNA cryptic pocket allosteric site",
        "PCNA sliding clamp protein interaction site",
        "graph neural network protein pocket prediction",
        "PocketMiner cryptic binding site",
        "PCNA inhibitor drug discovery",
    ],
    "arxiv": [
        "graph neural network protein structure pocket",
        "GNN allosteric site prediction",
        "equivariant graph network protein binding",
    ],
    "zenodo": [
        "cryptosite pocket dataset",
        "PCNA structure dataset",
        "protein binding site benchmark",
    ],
}

GNN_PCNA_YOUTUBE = [
    "PCNA protein structure function",
    "cryptic pocket drug discovery AlphaFold",
    "graph neural network protein structure prediction",
    "GATv2 molecular property prediction",
    "allosteric binding site computational biology",
]


def stage_crawl(topic: str, output_dir: Path, workers: int = 6) -> Path:
    from agents.crawler_agent import CrawlerAgent, PubMedSource, ArXivSource, ZenodoSource

    print(f"\n{'─'*55}")
    print(f"  Stage 1: CRAWL")
    print(f"{'─'*55}")

    crawler = CrawlerAgent(
        topic=topic,
        keywords=["PCNA", "cryptic pocket", "GNN", "graph neural network", "allosteric"],
        output_dir=output_dir,
        workers=workers,
        min_relevance=0.08,
    )
    for q in GNN_PCNA_QUERIES["pubmed"]:
        crawler.add_source(PubMedSource(queries=[q]))
    for q in GNN_PCNA_QUERIES["arxiv"]:
        crawler.add_source(ArXivSource(query=q))
    for q in GNN_PCNA_QUERIES["zenodo"]:
        crawler.add_source(ZenodoSource(queries=[q]))

    catalog = crawler.run()
    catalog_path = output_dir / "catalog.json"

    stats = catalog.get("stats", {})
    print(f"\n  Crawl complete: {stats.get('total', 0)} fetched, {stats.get('passed', 0)} passed")
    return catalog_path


def stage_verify(catalog_path: Path, domain: str) -> Path:
    from agents.verifier_agent import VerifierAgent

    print(f"\n{'─'*55}")
    print(f"  Stage 2: VERIFY (Gemma L6)")
    print(f"{'─'*55}")

    verifier = VerifierAgent(
        domain=domain,
        scoring_guide=(
            "10=direct PCNA cryptic pocket data or GNN pocket method, "
            "8=related protein pocket/GNN methods, "
            "6=general protein structure/ML, "
            "4=tangentially related biology, "
            "1=unrelated"
        ),
        min_pass_score=6,
        auto_approve_types=["pdb_structure", "structure"],
    )

    if not verifier.health_check():
        print("  [WARN] Ollama offline — skipping Gemma verification")
        return catalog_path

    verified_path = verifier.verify_catalog(catalog_path)
    print(f"  Verified catalog: {verified_path}")
    return verified_path


def stage_vault(catalog_path: Path, vault_dir: Path, project_name: str) -> dict:
    from agents.hub_writer import HubWriter

    print(f"\n{'─'*55}")
    print(f"  Stage 3: VAULT")
    print(f"{'─'*55}")

    writer = HubWriter(
        vault_dir=vault_dir,
        project_name=project_name,
        min_gemma=6,
        min_relevance=0.08,
    )
    stats = writer.write_catalog(catalog_path)
    print(f"  Knowledge graph: {vault_dir / 'KNOWLEDGE_GRAPH.md'}")
    return stats


def stage_youtube(vault_dir: Path) -> dict:
    from agents.research_pipeline import ResearchPipeline

    print(f"\n{'─'*55}")
    print(f"  Stage 4: YOUTUBE → NOTEBOOKLM")
    print(f"{'─'*55}")

    results = {}
    pipeline = ResearchPipeline(vault_dir=vault_dir)

    for topic in GNN_PCNA_YOUTUBE[:3]:
        try:
            result = pipeline.run(
                topic=topic,
                n_videos=4,
                artifact_types=["report", "flashcards"],
            )
            results[topic] = {"videos": len(result.videos), "artifacts": list(result.artifacts.keys())}
            print(f"  [{topic[:40]}] {len(result.videos)} videos")
        except Exception as e:
            results[topic] = {"error": str(e)}
            print(f"  [{topic[:40]}] FAILED: {e}")

    return results


def stage_briefing(run_stats: dict) -> str:
    from agents.base_agent import OllamaAgent

    print(f"\n{'─'*55}")
    print(f"  Stage 5: BRIEFING")
    print(f"{'─'*55}")

    agent = OllamaAgent()
    if not agent.health_check():
        return "Ollama offline — no briefing generated"

    prompt = (
        f"GNN-PCNA pipeline run completed.\n\n"
        f"Results:\n{json.dumps(run_stats, indent=2)}\n\n"
        "Summarize what was accomplished: how many papers crawled/verified, "
        "what vault notes were created, what YouTube research ran. "
        "Flag any critical findings or high-relevance records. "
        "What should I look at first? Under 200 words, bullet points."
    )
    return agent.chat(prompt, stream=False, print_stream=False)


def main() -> None:
    parser = argparse.ArgumentParser(description="GNN-PCNA research data pipeline")
    parser.add_argument("--topic", default="PCNA cryptic pocket graph neural network")
    parser.add_argument("--output", default="data/gnn_pcna")
    parser.add_argument("--vault", default="", help="Obsidian vault dir")
    parser.add_argument("--project", default="GNN-PCNA")
    parser.add_argument("--stages", nargs="+", choices=STAGES, default=["crawl", "verify", "vault"])
    parser.add_argument("--all", action="store_true", help="Run all stages")
    parser.add_argument("--workers", type=int, default=6)
    args = parser.parse_args()

    stages_to_run = STAGES if args.all else args.stages
    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)

    vault_dir = Path(args.vault) if args.vault else output_dir / "vault"
    vault_dir.mkdir(parents=True, exist_ok=True)

    print(f"\n{'='*55}")
    print(f"  GNN-PCNA Pipeline — {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M')} UTC")
    print(f"  Topic: {args.topic}")
    print(f"  Stages: {', '.join(stages_to_run)}")
    print(f"  Output: {output_dir}")
    print(f"{'='*55}")

    t0 = time.monotonic()
    run_stats: dict = {}
    catalog_path = output_dir / "catalog.json"

    if "crawl" in stages_to_run:
        catalog_path = stage_crawl(args.topic, output_dir, workers=args.workers)
        run_stats["crawl"] = {"catalog": str(catalog_path)}

    if "verify" in stages_to_run and catalog_path.exists():
        catalog_path = stage_verify(catalog_path, args.topic)
        run_stats["verify"] = {"verified": str(catalog_path)}

    if "vault" in stages_to_run and catalog_path.exists():
        vault_stats = stage_vault(catalog_path, vault_dir, args.project)
        run_stats["vault"] = vault_stats

    if "youtube" in stages_to_run:
        yt_stats = stage_youtube(vault_dir)
        run_stats["youtube"] = yt_stats

    if "briefing" in stages_to_run:
        briefing = stage_briefing(run_stats)
        run_stats["briefing"] = briefing

    elapsed = time.monotonic() - t0
    report_path = output_dir / f"{datetime.now().strftime('%Y-%m-%d')}_pipeline_report.json"
    report_path.write_text(json.dumps(run_stats, indent=2), encoding="utf-8")

    print(f"\n{'='*55}")
    print(f"  Pipeline complete — {elapsed:.0f}s")
    print(f"  Report: {report_path}")
    print(f"{'='*55}")

    if "briefing" in run_stats:
        print(f"\n{run_stats['briefing']}")


if __name__ == "__main__":
    main()
