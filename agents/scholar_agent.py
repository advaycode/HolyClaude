"""
scholar_agent.py — Playwright-based scholarship and research program scraper.

Scrapes multiple scholarship databases, filters by eligibility, ranks by deadline,
deduplicates by URL hash, and writes Obsidian vault notes.

Usage:
    agent = ScholarAgent(min_amount=500, deadline_within_days=90)
    results = agent.run(output_dir=Path("data/scholarships"))

    # CLI:
    python agents/scholar_agent.py --min-amount 500 --deadline-within 90 --vault C:/Users/advay/Obsidian/Scholarships
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
import sys
from dataclasses import dataclass, field, asdict
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Optional

# ── scholarship record ────────────────────────────────────────────────────────

@dataclass
class Scholarship:
    name: str
    url: str
    amount: float = 0.0          # USD, 0 if unknown
    deadline: str = ""           # ISO date or raw string
    deadline_parsed: str = ""    # ISO if parseable
    description: str = ""
    eligibility: list[str] = field(default_factory=list)
    source: str = ""
    tags: list[str] = field(default_factory=list)
    uid: str = ""                # SHA256[:12] of URL

    def __post_init__(self):
        if not self.uid:
            self.uid = hashlib.sha256(self.url.encode()).hexdigest()[:12]

    def days_until_deadline(self) -> Optional[int]:
        try:
            dl = datetime.fromisoformat(self.deadline_parsed).date()
            return (dl - date.today()).days
        except Exception:
            return None

    def urgency_label(self) -> str:
        days = self.days_until_deadline()
        if days is None: return "unknown"
        if days < 0:     return "expired"
        if days <= 14:   return "urgent"
        if days <= 45:   return "soon"
        return "open"

    def to_dict(self) -> dict:
        return {**asdict(self), "days_until": self.days_until_deadline(), "urgency": self.urgency_label()}


# ── date parsing ───────────────────────────────────────────────────────────────

_DATE_PATTERNS = [
    r"(\w+ \d{1,2},? \d{4})",
    r"(\d{1,2}/\d{1,2}/\d{4})",
    r"(\d{4}-\d{2}-\d{2})",
    r"((?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]* \d{1,2},? \d{4})",
]

def _parse_deadline(raw: str) -> str:
    for pattern in _DATE_PATTERNS:
        m = re.search(pattern, raw, re.IGNORECASE)
        if m:
            s = m.group(1).strip().rstrip(",")
            for fmt in ["%B %d %Y", "%b %d %Y", "%m/%d/%Y", "%Y-%m-%d", "%B %d, %Y", "%b %d, %Y"]:
                try:
                    return datetime.strptime(s, fmt).strftime("%Y-%m-%d")
                except ValueError:
                    continue
    return ""

def _parse_amount(raw: str) -> float:
    m = re.search(r"\$[\d,]+(?:\.\d{2})?", raw.replace(",", ""))
    if m:
        try:
            return float(re.sub(r"[^\d.]", "", m.group()))
        except ValueError:
            pass
    return 0.0


# ── source scrapers ───────────────────────────────────────────────────────────

class ScholarshipSource:
    name: str = "base"

    def scrape(self, pw) -> list[Scholarship]:
        raise NotImplementedError


class CollegeBoardSource(ScholarshipSource):
    name = "College Board"

    def scrape(self, pw) -> list[Scholarship]:
        url = "https://bigfuture.collegeboard.org/scholarships"
        schema = {
            "name": ".scholarship-title",
            "amount": ".award-amount",
            "deadline": ".deadline-date",
            "description": ".scholarship-description",
            "link": "a.scholarship-title@href",
        }
        try:
            items = pw.scrape_structured(url, schema, multi=True)
            results = []
            for item in items[:30]:
                s = Scholarship(
                    name=item.get("name", ""),
                    url=item.get("link", url),
                    amount=_parse_amount(item.get("amount", "")),
                    deadline=item.get("deadline", ""),
                    deadline_parsed=_parse_deadline(item.get("deadline", "")),
                    description=item.get("description", "")[:400],
                    source=self.name,
                    tags=["college-board"],
                )
                if s.name:
                    results.append(s)
            return results
        except Exception as e:
            print(f"[scholar] {self.name} failed: {e}", file=sys.stderr)
            return []


class GoingMerrySource(ScholarshipSource):
    name = "Going Merry"

    def scrape(self, pw) -> list[Scholarship]:
        url = "https://www.goingmerry.com/scholarships"
        schema = {
            "name": ".scholarship-card-title, h3",
            "amount": ".award, .scholarship-amount",
            "deadline": ".deadline, .due-date",
            "description": ".description, p",
            "link": "a@href",
        }
        try:
            items = pw.scrape_structured(url, schema, multi=True)
            results = []
            for item in items[:30]:
                s = Scholarship(
                    name=item.get("name", ""),
                    url=item.get("link", url),
                    amount=_parse_amount(item.get("amount", "")),
                    deadline=item.get("deadline", ""),
                    deadline_parsed=_parse_deadline(item.get("deadline", "")),
                    description=item.get("description", "")[:400],
                    source=self.name,
                    tags=["going-merry"],
                )
                if s.name:
                    results.append(s)
            return results
        except Exception as e:
            print(f"[scholar] {self.name} failed: {e}", file=sys.stderr)
            return []


class ScholarshipsComSource(ScholarshipSource):
    name = "Scholarships.com"

    def scrape(self, pw) -> list[Scholarship]:
        url = "https://www.scholarships.com/financial-aid/college-scholarships/scholarship-directory/deadline/scholarships-with-upcoming-deadlines"
        schema = {
            "name": ".scholarship-name, h3",
            "amount": ".scholarship-amount",
            "deadline": ".scholarship-deadline",
            "description": ".scholarship-description",
            "link": "a.scholarship-name@href, a@href",
        }
        try:
            items = pw.scrape_structured(url, schema, multi=True)
            results = []
            for item in items[:25]:
                s = Scholarship(
                    name=item.get("name", ""),
                    url=item.get("link", url),
                    amount=_parse_amount(item.get("amount", "")),
                    deadline=item.get("deadline", ""),
                    deadline_parsed=_parse_deadline(item.get("deadline", "")),
                    description=item.get("description", "")[:400],
                    source=self.name,
                    tags=["scholarships-com"],
                )
                if s.name:
                    results.append(s)
            return results
        except Exception as e:
            print(f"[scholar] {self.name} failed: {e}", file=sys.stderr)
            return []


DEFAULT_SOURCES = [CollegeBoardSource, GoingMerrySource, ScholarshipsComSource]


# ── scholar agent ──────────────────────────────────────────────────────────────

class ScholarAgent:
    """
    Multi-source scholarship scraper with eligibility filtering and vault output.

    Runs Playwright on multiple scholarship databases, deduplicates by URL hash,
    filters by amount/deadline, sorts by urgency, and writes Obsidian notes.
    """

    def __init__(
        self,
        min_amount: float = 0.0,
        deadline_within_days: int = 365,
        sources: Optional[list] = None,
        tags_filter: Optional[list[str]] = None,
        headless: bool = True,
    ) -> None:
        self.min_amount = min_amount
        self.deadline_within_days = deadline_within_days
        self.sources = [cls() for cls in (sources or DEFAULT_SOURCES)]
        self.tags_filter = tags_filter
        self.headless = headless

    def _passes_filter(self, s: Scholarship) -> bool:
        if self.min_amount > 0 and s.amount > 0 and s.amount < self.min_amount:
            return False
        days = s.days_until_deadline()
        if days is not None:
            if days < 0:
                return False
            if days > self.deadline_within_days:
                return False
        return True

    def _deduplicate(self, scholarships: list[Scholarship]) -> list[Scholarship]:
        seen: set[str] = set()
        out: list[Scholarship] = []
        for s in scholarships:
            if s.uid not in seen:
                seen.add(s.uid)
                out.append(s)
        return out

    def run(self, output_dir: Path = Path("data/scholarships")) -> list[Scholarship]:
        from agents.playwright_agent import PlaywrightAgent

        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        all_scholarships: list[Scholarship] = []

        with PlaywrightAgent(headless=self.headless) as pw:
            for source in self.sources:
                print(f"\n[scholar] Scraping {source.name}...", file=sys.stderr)
                results = source.scrape(pw)
                print(f"  → {len(results)} found", file=sys.stderr)
                all_scholarships.extend(results)

        unique = self._deduplicate(all_scholarships)
        filtered = [s for s in unique if self._passes_filter(s)]

        # Sort: urgent first, then by amount descending
        def sort_key(s: Scholarship):
            days = s.days_until_deadline()
            return (days if days is not None else 9999, -s.amount)

        filtered.sort(key=sort_key)

        print(f"\n[scholar] {len(all_scholarships)} total → {len(unique)} unique → {len(filtered)} passing filters")

        # Save JSON catalog
        catalog_path = output_dir / f"{date.today()}_scholarships.json"
        catalog_path.write_text(
            json.dumps([s.to_dict() for s in filtered], indent=2),
            encoding="utf-8",
        )
        print(f"[scholar] Catalog: {catalog_path}")

        # Save CSV
        csv_path = output_dir / f"{date.today()}_scholarships.csv"
        if filtered:
            with csv_path.open("w", newline="", encoding="utf-8") as f:
                w = csv.DictWriter(f, fieldnames=["name", "amount", "deadline_parsed", "urgency", "days_until", "source", "url"])
                w.writeheader()
                for s in filtered:
                    w.writerow({k: s.to_dict().get(k, "") for k in w.fieldnames})
            print(f"[scholar] CSV: {csv_path}")

        self._print_summary(filtered)
        return filtered

    def write_vault(self, scholarships: list[Scholarship], vault_dir: Path) -> None:
        vault_dir = Path(vault_dir)
        vault_dir.mkdir(parents=True, exist_ok=True)

        for s in scholarships:
            fname = re.sub(r"[^\w\s-]", "", s.name).strip().replace(" ", "_")[:60]
            dest = vault_dir / f"{fname}_{s.uid}.md"
            if dest.exists():
                continue
            content = (
                f"---\n"
                f"type: scholarship\n"
                f"name: \"{s.name}\"\n"
                f"amount: {s.amount}\n"
                f"deadline: {s.deadline_parsed or s.deadline}\n"
                f"urgency: {s.urgency_label()}\n"
                f"days_until: {s.days_until_deadline()}\n"
                f"source: {s.source}\n"
                f"uid: {s.uid}\n"
                f"indexed: {date.today()}\n"
                f"---\n\n"
                f"# {s.name}\n\n"
                f"**Amount**: ${s.amount:,.0f}\n"
                f"**Deadline**: {s.deadline_parsed or s.deadline} ({s.urgency_label()})\n"
                f"**Source**: {s.source}\n\n"
                f"## Description\n\n{s.description}\n\n"
                f"## Eligibility\n\n"
                + ("\n".join(f"- {e}" for e in s.eligibility) or "- See link")
                + f"\n\n[Apply →]({s.url})\n\n"
                f"## Checklist\n\n"
                f"- [ ] Check eligibility\n"
                f"- [ ] Prepare materials\n"
                f"- [ ] Submit by {s.deadline_parsed or s.deadline}\n"
            )
            dest.write_text(content, encoding="utf-8")

        print(f"[scholar] Wrote {len(scholarships)} notes → {vault_dir}")

    @staticmethod
    def _print_summary(scholarships: list[Scholarship]) -> None:
        print(f"\n{'='*60}")
        print(f"  SCHOLARSHIP RESULTS — {date.today()}")
        print(f"{'='*60}")
        for s in scholarships[:15]:
            days = s.days_until_deadline()
            days_str = f"{days}d" if days is not None else "?"
            amt_str = f"${s.amount:,.0f}" if s.amount else "?"
            print(f"  [{s.urgency_label().upper():<7}] {s.name[:40]:<42} {amt_str:<10} due in {days_str}")
        if len(scholarships) > 15:
            print(f"  ... and {len(scholarships)-15} more")
        print(f"{'='*60}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Scholarship scraper")
    parser.add_argument("--min-amount", type=float, default=0, help="Minimum award amount in USD")
    parser.add_argument("--deadline-within", type=int, default=365, help="Only show deadlines within N days")
    parser.add_argument("--output", default="data/scholarships", help="Output directory")
    parser.add_argument("--vault", default="", help="Obsidian vault dir for notes")
    parser.add_argument("--headed", action="store_true", help="Show browser window")
    args = parser.parse_args()

    agent = ScholarAgent(
        min_amount=args.min_amount,
        deadline_within_days=args.deadline_within,
        headless=not args.headed,
    )
    results = agent.run(output_dir=Path(args.output))

    if args.vault:
        agent.write_vault(results, vault_dir=Path(args.vault))


if __name__ == "__main__":
    main()
