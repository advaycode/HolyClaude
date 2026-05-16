#!/usr/bin/env python
"""
cli.py — HolyClaude unified command-line interface.

Usage:
    python cli.py research "PCNA cryptic pocket GNN" --n 6 --artifacts report flashcards
    python cli.py crawl "protein folding" --keywords "GNN" "AlphaFold" --verify
    python cli.py ask "What is focal loss and when should I use it?"
    python cli.py implement docs/plans/2026-05-15_parse_pdb.md --project C:/Users/advay/GNN_PNCA
    python cli.py review src/data_processing/parse_pdb.py --project C:/Users/advay/GNN_PNCA
    python cli.py plan "Implement graph_construction for PCNA homotrimer" --project C:/Users/advay/GNN_PNCA
    python cli.py optimize "your prompt" --domain "GNN-PCNA"
    python cli.py study --subject ap-physics --artifact video
    python cli.py overnight --research "AlphaFold binding" --study ap-physics
    python cli.py scrape https://example.com --schema title:h1 links:a@href
    python cli.py status
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

# ── status ────────────────────────────────────────────────────────────────────

def cmd_status(args) -> None:
    from agents.base_agent import OllamaAgent
    agent = OllamaAgent()
    ollama_ok = agent.health_check()
    models = agent.list_models() if ollama_ok else []

    yt = Path.home() / "tools" / "yt-research" / "yt_research.py"
    nlm = Path.home() / "tools" / "notebooklm" / "notebooklm_skill.py"

    print("HolyClaude Status")
    print(f"  Ollama:      {'RUNNING' if ollama_ok else 'OFFLINE — run: ollama serve'}")
    if ollama_ok:
        print(f"  Models:      {', '.join(models) or 'none'}")
    print(f"  gemma3:4b:   {'AVAILABLE' if 'gemma3:4b' in models else 'MISSING — ollama pull gemma3:4b'}")
    print(f"  yt-research: {'OK' if yt.exists() else 'MISSING — see STACK.md'}")
    print(f"  notebooklm:  {'OK' if nlm.exists() else 'MISSING — see STACK.md'}")

    for pkg in ["openai", "requests", "beautifulsoup4", "mcp", "playwright"]:
        try:
            __import__(pkg.replace("-", "_"))
            print(f"  pkg:{pkg:<16} installed")
        except ImportError:
            print(f"  pkg:{pkg:<16} MISSING — pip install {pkg}")


# ── ask ───────────────────────────────────────────────────────────────────────

def cmd_ask(args) -> None:
    from agents.base_agent import OllamaAgent
    agent = OllamaAgent(model=args.model)
    agent.require_ollama()
    prompt = " ".join(args.prompt)
    system = "Answer concisely. Use bullet points and code blocks where helpful."
    agent.chat(prompt, system=system)


# ── optimize ──────────────────────────────────────────────────────────────────

def cmd_optimize(args) -> None:
    from agents.prompt_optimizer import PromptOptimizer
    vault = Path(args.vault) if args.vault else None
    opt = PromptOptimizer(
        vault_dir=vault,
        domain_context=args.domain,
        run_local=args.execute,
        model=args.model,
    )
    prompt = " ".join(args.prompt)
    plan = opt.optimize(
        prompt,
        use_llm_classify=args.llm_classify,
        decompose=args.decompose,
    )
    print(plan.render())
    if args.execute:
        print("\n=== EXECUTING ===\n")
        plan.execute()


# ── implement ─────────────────────────────────────────────────────────────────

def cmd_implement(args) -> None:
    from agents.code_agent import CodeAgent
    agent = CodeAgent(
        project_root=Path(args.project) if args.project else None,
        model=args.model,
    )
    agent.require_ollama()
    agent.implement(Path(args.plan))


# ── review ────────────────────────────────────────────────────────────────────

def cmd_review(args) -> None:
    from agents.code_agent import CodeAgent
    agent = CodeAgent(
        project_root=Path(args.project) if args.project else None,
        model=args.model,
    )
    agent.require_ollama()
    agent.review(Path(args.file))


# ── plan ──────────────────────────────────────────────────────────────────────

def cmd_plan(args) -> None:
    from agents.code_agent import CodeAgent
    agent = CodeAgent(
        project_root=Path(args.project) if args.project else None,
        model=args.model,
    )
    agent.require_ollama()
    agent.plan(" ".join(args.task))


# ── research ──────────────────────────────────────────────────────────────────

def cmd_research(args) -> None:
    from agents.research_pipeline import ResearchPipeline, ARTIFACT_TYPES
    vault = Path(args.vault) if args.vault else None
    pipeline = ResearchPipeline(vault_dir=vault)
    pipeline.run(
        topic=" ".join(args.topic),
        n_videos=args.n,
        artifact_types=args.artifacts,
        focus_question=args.question,
    )


# ── crawl ─────────────────────────────────────────────────────────────────────

def cmd_crawl(args) -> None:
    from agents.crawler_agent import CrawlerAgent, PubMedSource, ArXivSource, ZenodoSource
    topic = " ".join(args.topic)
    keywords = args.keywords or topic.split()
    output = Path(args.output)

    crawler = CrawlerAgent(
        topic=topic,
        keywords=keywords,
        output_dir=output,
        workers=args.workers,
        min_relevance=args.min_relevance,
    )
    crawler.add_source(PubMedSource(queries=[f"{topic} {kw}" for kw in keywords[:2]]))
    crawler.add_source(ArXivSource(query=f"{topic} {keywords[0]}" if keywords else topic))
    if args.zenodo:
        crawler.add_source(ZenodoSource(queries=[topic]))

    catalog = crawler.run()
    catalog_path = output / "catalog.json"

    if args.verify and catalog.get("stats", {}).get("passed", 0) > 0:
        from agents.verifier_agent import VerifierAgent
        verifier = VerifierAgent(domain=topic, model=args.model)
        if verifier.health_check():
            verifier.verify_catalog(catalog_path)

    if args.vault:
        from agents.hub_writer import HubWriter
        writer = HubWriter(vault_dir=Path(args.vault), project_name=topic)
        writer.write_catalog(catalog_path)


# ── study ─────────────────────────────────────────────────────────────────────

def cmd_study(args) -> None:
    from agents.study_agent import StudyAgent
    subjects = {"ap-physics": StudyAgent.ap_physics, "ap-stats": StudyAgent.ap_stats}
    builder = subjects.get(args.subject)
    if not builder:
        topics = [t.strip() for t in args.subject.split(",")]
        agent = StudyAgent.custom(topics=topics, subject="Custom")
    else:
        agent = builder()
    agent.run_daily(
        n_videos=args.n,
        artifact=args.artifact,
        force_topic=args.force_topic,
        dry_run=args.dry_run,
    )


# ── overnight ─────────────────────────────────────────────────────────────────

def cmd_overnight(args) -> None:
    from agents.overnight_agent import OvernightAgent
    vault = Path(args.vault) if args.vault else None
    agent = OvernightAgent(vault_dir=vault)

    if args.tasks:
        agent.load_tasks_from_json(Path(args.tasks))
    if args.research:
        for t in args.research:
            agent.add_research(t)
    if args.study:
        agent.add_study(subject=args.study)
    if args.crawl:
        for t in args.crawl:
            agent.add_crawl(t)

    if not agent._tasks:
        print("No tasks. Use --research, --study, --crawl, or --tasks.")
        sys.exit(1)
    agent.run(parallel=args.parallel)


# ── scrape ────────────────────────────────────────────────────────────────────

def cmd_scrape(args) -> None:
    from agents.playwright_agent import PlaywrightAgent
    schema: dict[str, str] = {}
    for pair in (args.schema or []):
        if ":" in pair:
            k, v = pair.split(":", 1)
            schema[k] = v

    with PlaywrightAgent(headless=not args.headed) as pw:
        if args.screenshot:
            path = pw.screenshot(args.url, Path(args.screenshot))
            print(f"Screenshot: {path}")
        elif schema:
            import json
            data = pw.scrape_structured(args.url, schema, multi=args.multi)
            print(json.dumps(data, indent=2))
        else:
            links = pw.extract_links(args.url)
            for link in links[:50]:
                print(link)


# ── main ──────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        prog="holy",
        description="HolyClaude — unified AI agent CLI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--model", default="gemma3:4b", help="Ollama model")
    sub = parser.add_subparsers(dest="command", required=True)

    # status
    sub.add_parser("status", help="Check all tools and Ollama status")

    # ask
    p = sub.add_parser("ask", help="Ask Ollama a question")
    p.add_argument("prompt", nargs="+")

    # optimize
    p = sub.add_parser("optimize", help="Optimize a prompt through the routing pipeline")
    p.add_argument("prompt", nargs="+")
    p.add_argument("--domain", default="", help="Domain context")
    p.add_argument("--vault", default="", help="Vault dir for knowledge injection")
    p.add_argument("--execute", action="store_true", help="Execute through Ollama")
    p.add_argument("--llm-classify", action="store_true")
    p.add_argument("--decompose", action="store_true")

    # implement
    p = sub.add_parser("implement", help="Implement from a plan file via Ollama")
    p.add_argument("plan", help="Path to plan .md file")
    p.add_argument("--project", default="", help="Project root (for CLAUDE.md/REPO_MAP)")

    # review
    p = sub.add_parser("review", help="Review a source file via Ollama")
    p.add_argument("file", help="File to review")
    p.add_argument("--project", default="", help="Project root")

    # plan
    p = sub.add_parser("plan", help="Generate an implementation plan via Ollama")
    p.add_argument("task", nargs="+")
    p.add_argument("--project", default="", help="Project root")

    # research
    p = sub.add_parser("research", help="YouTube → NotebookLM research pipeline")
    p.add_argument("topic", nargs="+")
    p.add_argument("--n", type=int, default=5)
    p.add_argument("--artifacts", nargs="+", default=["report"])
    p.add_argument("--question", default="")
    p.add_argument("--vault", default="")

    # crawl
    p = sub.add_parser("crawl", help="Multi-source web crawler + validate + vault")
    p.add_argument("topic", nargs="+")
    p.add_argument("--keywords", nargs="+", default=[])
    p.add_argument("--output", default="data/crawl")
    p.add_argument("--workers", type=int, default=4)
    p.add_argument("--min-relevance", type=float, default=0.10)
    p.add_argument("--verify", action="store_true")
    p.add_argument("--zenodo", action="store_true")
    p.add_argument("--vault", default="")

    # study
    p = sub.add_parser("study", help="Daily study pipeline (YouTube → NotebookLM)")
    p.add_argument("--subject", default="ap-physics", help="ap-physics, ap-stats, or topic list")
    p.add_argument("--artifact", default="video")
    p.add_argument("--n", type=int, default=4)
    p.add_argument("--force-topic", type=int, default=None)
    p.add_argument("--dry-run", action="store_true")

    # overnight
    p = sub.add_parser("overnight", help="Run background tasks + morning briefing")
    p.add_argument("--research", nargs="+", metavar="TOPIC")
    p.add_argument("--study", default="")
    p.add_argument("--crawl", nargs="+", metavar="TOPIC")
    p.add_argument("--tasks", help="JSON file with task list")
    p.add_argument("--vault", default="")
    p.add_argument("--parallel", action="store_true")

    # scrape
    p = sub.add_parser("scrape", help="Playwright browser scraper")
    p.add_argument("url")
    p.add_argument("--schema", nargs="+", metavar="field:selector", help="CSS selector schema")
    p.add_argument("--screenshot", default="", help="Save screenshot to path")
    p.add_argument("--multi", action="store_true", help="Scrape multiple items")
    p.add_argument("--headed", action="store_true", help="Show browser window")

    args = parser.parse_args()
    handlers = {
        "status": cmd_status, "ask": cmd_ask, "optimize": cmd_optimize,
        "implement": cmd_implement, "review": cmd_review, "plan": cmd_plan,
        "research": cmd_research, "crawl": cmd_crawl,
        "study": cmd_study, "overnight": cmd_overnight, "scrape": cmd_scrape,
    }
    handlers[args.command](args)


if __name__ == "__main__":
    main()
