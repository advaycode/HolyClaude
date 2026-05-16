"""
scholar_flow.py — Full scholarship discovery pipeline.

Stages:
  1. scrape     — Playwright multi-source scholarship scrape
  2. filter     — Amount, deadline, eligibility filter
  3. rank       — Sort by urgency + amount
  4. vault      — Write Obsidian notes
  5. briefing   — Ollama summary: what to apply to first

Usage:
    python workflows/scholar_flow.py --min-amount 500 --deadline-within 90 --vault C:/Users/advay/Obsidian/Scholarships
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


def stage_scrape(
    min_amount: float,
    deadline_within: int,
    output_dir: Path,
    headless: bool = True,
) -> list:
    from agents.scholar_agent import ScholarAgent

    print(f"\n{'─'*55}")
    print(f"  Stage 1: SCRAPE")
    print(f"{'─'*55}")

    agent = ScholarAgent(
        min_amount=min_amount,
        deadline_within_days=deadline_within,
        headless=headless,
    )
    return agent.run(output_dir=output_dir)


def stage_vault(scholarships: list, vault_dir: Path) -> None:
    from agents.scholar_agent import ScholarAgent

    print(f"\n{'─'*55}")
    print(f"  Stage 2: VAULT")
    print(f"{'─'*55}")

    agent = ScholarAgent()
    agent.write_vault(scholarships, vault_dir)


def stage_briefing(scholarships: list) -> str:
    from agents.base_agent import OllamaAgent

    print(f"\n{'─'*55}")
    print(f"  Stage 3: BRIEFING")
    print(f"{'─'*55}")

    agent = OllamaAgent()
    if not agent.health_check():
        lines = ["Scholarship Briefing (Ollama offline)", ""]
        for s in scholarships[:10]:
            days = s.days_until_deadline()
            lines.append(f"- {s.name}: ${s.amount:,.0f} — due in {days}d ({s.urgency_label()})")
        return "\n".join(lines)

    if not scholarships:
        return "No scholarships found."

    top = scholarships[:12]
    summary_lines = [f"Scholarship scrape: {len(scholarships)} results", ""]
    for s in top:
        days = s.days_until_deadline()
        summary_lines.append(
            f"- {s.name} | ${s.amount:,.0f} | due in {days}d | {s.source}"
        )

    prompt = "\n".join(summary_lines)
    system = (
        "You are advising a high school student on scholarship applications. "
        "Given this list, rank the top 5 to apply to first based on urgency, amount, and realistic eligibility. "
        "For each: name, why it's a priority, and any red flags. Under 250 words."
    )
    return agent.chat(prompt, system=system, stream=False, print_stream=False)


def main() -> None:
    parser = argparse.ArgumentParser(description="Scholarship discovery pipeline")
    parser.add_argument("--min-amount", type=float, default=500)
    parser.add_argument("--deadline-within", type=int, default=120)
    parser.add_argument("--output", default="data/scholarships")
    parser.add_argument("--vault", default="", help="Obsidian vault dir")
    parser.add_argument("--headed", action="store_true")
    parser.add_argument("--no-briefing", action="store_true")
    args = parser.parse_args()

    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)

    print(f"\n{'='*55}")
    print(f"  Scholar Flow — {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M')} UTC")
    print(f"  Min amount: ${args.min_amount:,.0f}")
    print(f"  Deadline within: {args.deadline_within} days")
    print(f"{'='*55}")

    t0 = time.monotonic()

    scholarships = stage_scrape(
        min_amount=args.min_amount,
        deadline_within=args.deadline_within,
        output_dir=output_dir,
        headless=not args.headed,
    )

    if args.vault and scholarships:
        stage_vault(scholarships, vault_dir=Path(args.vault))

    briefing = ""
    if not args.no_briefing:
        briefing = stage_briefing(scholarships)

    elapsed = time.monotonic() - t0

    print(f"\n{'='*55}")
    print(f"  Scholar Flow complete — {elapsed:.0f}s")
    print(f"  Found: {len(scholarships)} scholarships")
    print(f"{'='*55}")

    if briefing:
        print(f"\n=== BRIEFING ===\n{briefing}")


if __name__ == "__main__":
    main()
