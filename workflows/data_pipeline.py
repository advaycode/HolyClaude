"""
data_pipeline.py — End-to-end research data pipeline.

Chains: Crawl → L6 Verify → Vault Write → (optional) Train

Usage:
    python workflows/data_pipeline.py \
        --topic "protein pocket prediction" \
        --keywords "cryptic pocket" "GNN" "graph neural network" \
        --sources pubmed arxiv zenodo \
        --output data/my_research

    # With Gemma verification:
    python workflows/data_pipeline.py --topic "PCNA" --keywords "PCNA" --verify

    # Full pipeline with vault write:
    python workflows/data_pipeline.py --topic "PCNA" --keywords "PCNA" --verify --vault docs/knowledge
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(REPO_ROOT))

from agents import (
    CrawlerAgent, VerifierAgent, KnowledgeWriter,
    PubMedSource, ArXivSource, GitHubSource, ZenodoSource,
)

SOURCE_MAP = {
    "pubmed":  lambda topic, keywords: PubMedSource(queries=[f"{topic} {kw}" for kw in keywords[:2]]),
    "arxiv":   lambda topic, keywords: ArXivSource(query=f"{topic} {keywords[0]}" if keywords else topic),
    "zenodo":  lambda topic, keywords: ZenodoSource(queries=[f"{topic} {kw}" for kw in keywords[:2]]),
    "github":  lambda topic, keywords: None,  # requires explicit repos
}


def main() -> None:
    parser = argparse.ArgumentParser(description="HolyClaude research data pipeline")
    parser.add_argument("--topic",    required=True, help="Research topic (e.g. 'PCNA cryptic pocket')")
    parser.add_argument("--keywords", nargs="+", default=[], help="Relevance keywords for L4 scoring")
    parser.add_argument("--sources",  nargs="+", default=["pubmed", "arxiv"],
                        choices=list(SOURCE_MAP.keys()), help="Data sources to query")
    parser.add_argument("--output",   default="data/research", help="Output directory for catalog")
    parser.add_argument("--workers",  type=int, default=4)
    parser.add_argument("--min-relevance", type=float, default=0.10)
    parser.add_argument("--verify",   action="store_true", help="Run Gemma L6 verification")
    parser.add_argument("--vault",    help="Obsidian vault dir — write notes if provided")
    parser.add_argument("--model",    default="gemma3:4b", help="Ollama model for verification")
    parser.add_argument("--min-gemma", type=int, default=6, help="Minimum Gemma score to include in vault")
    args = parser.parse_args()

    output_dir = REPO_ROOT / args.output
    keywords = args.keywords or args.topic.split()

    # ── Stage 1: Crawl ────────────────────────────────────────────────────────
    print(f"\n{'='*60}")
    print(f"  STAGE 1: CRAWL")
    print(f"  Topic:    {args.topic}")
    print(f"  Keywords: {keywords}")
    print(f"  Sources:  {args.sources}")
    print(f"{'='*60}\n")

    crawler = CrawlerAgent(
        topic=args.topic,
        keywords=keywords,
        output_dir=output_dir,
        workers=args.workers,
        min_relevance=args.min_relevance,
        source_weights={"pubmed": 0.05, "arxiv": 0.04, "zenodo": 0.04},
    )

    for src_name in args.sources:
        build_fn = SOURCE_MAP.get(src_name)
        if build_fn:
            src = build_fn(args.topic, keywords)
            if src:
                crawler.add_source(src)

    catalog = crawler.run()
    catalog_path = output_dir / "catalog.json"

    passed = len(catalog.get("passed", []))
    print(f"\nCrawl complete: {passed} records passed validation")

    if passed == 0:
        print("No records — nothing to verify or write")
        return

    # ── Stage 2: Verify (optional) ────────────────────────────────────────────
    if args.verify:
        print(f"\n{'='*60}")
        print(f"  STAGE 2: VERIFY (Gemma L6)")
        print(f"{'='*60}\n")
        verifier = VerifierAgent(
            domain=args.topic,
            scoring_guide=f"10=directly relevant to {args.topic}, 7=method applicable, 5=tangential, 1=unrelated",
            model=args.model,
        )
        if verifier.health_check():
            verifier.verify_catalog(catalog_path)
        else:
            print(f"[warn] Ollama offline — skipping L6 verify. Start with: ollama serve")

    # ── Stage 3: Vault Write (optional) ───────────────────────────────────────
    if args.vault:
        print(f"\n{'='*60}")
        print(f"  STAGE 3: VAULT WRITE")
        print(f"  Vault: {args.vault}")
        print(f"{'='*60}\n")
        writer = KnowledgeWriter(
            vault_dir=Path(args.vault),
            min_gemma=args.min_gemma,
        )
        writer.write_catalog(catalog_path)

    print(f"\n{'='*60}")
    print(f"  PIPELINE COMPLETE")
    print(f"  Catalog: {catalog_path}")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()
