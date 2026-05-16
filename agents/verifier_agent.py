"""
verifier_agent.py — Ollama-powered credibility verifier for crawled records.

Wraps any Ollama model as an LLM judge for catalog records.
Layer 6 of the validation pipeline — runs after the 5-layer structural check.

Usage:
    verifier = VerifierAgent(
        domain="PCNA cryptic pocket prediction",
        scoring_guide="10=direct PCNA data, 7=GNN/pocket methods, 5=general protein, 1=unrelated",
    )
    catalog = verifier.verify_catalog(Path("data/catalog/catalog.json"))

    # Or verify a single record:
    score, reason = verifier.verify_record(record_dict)
"""
from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Optional

from .base_agent import OllamaAgent


class VerifierAgent(OllamaAgent):
    """
    LLM-based credibility verifier for catalog records.

    Scores each record 1-10 using a configurable rubric.
    PDB/structure records auto-approve at a fixed score.
    Papers and datasets go through LLM scoring.
    """

    MODEL = "gemma3:4b"
    TEMPERATURE = 0.1
    MAX_TOKENS = 80

    _SYSTEM_TEMPLATE = (
        "You are a data curator for a research project on {domain}. "
        "You evaluate whether a data source is directly useful for this project."
    )

    _PROMPT_TEMPLATE = """\
Evaluate this data source for relevance to: {domain}

Title: {title}
Description: {description}
Type: {record_type}
Source database: {source}

Scoring guide:
{scoring_guide}

Reply with EXACTLY two lines:
<integer score 1-10>
<one-line reason, max 120 characters>
"""

    def __init__(
        self,
        domain: str,
        scoring_guide: str = "10=highly relevant, 5=somewhat relevant, 1=unrelated",
        auto_approve_types: Optional[list[str]] = None,
        auto_approve_score: int = 7,
        min_pass_score: int = 6,
        model: str | None = None,
    ) -> None:
        super().__init__(model=model)
        self.domain = domain
        self.scoring_guide = scoring_guide
        self.auto_approve_types = set(auto_approve_types or [])
        self.auto_approve_score = auto_approve_score
        self.min_pass_score = min_pass_score
        self.system = self._SYSTEM_TEMPLATE.format(domain=domain)

    def verify_record(self, record: dict) -> tuple[int, str]:
        """
        Score one catalog record.

        Returns:
            (score, reason)  — score 1-10, reason is a short string.
        """
        rtype = record.get("record_type", "")

        if rtype in self.auto_approve_types:
            return self.auto_approve_score, f"{rtype} auto-approved"

        title = (record.get("title") or "")[:200]
        description = (record.get("description") or "")[:400]

        prompt = self._PROMPT_TEMPLATE.format(
            domain=self.domain,
            title=title,
            description=description,
            record_type=rtype,
            source=record.get("source", ""),
            scoring_guide=self.scoring_guide,
        )

        try:
            text = self.chat(prompt, stream=False, print_stream=False)
            lines = [l.strip() for l in text.splitlines() if l.strip()]
            score = max(1, min(10, int(lines[0])))
            reason = lines[1] if len(lines) > 1 else "no reason"
            return score, reason[:150]
        except (ValueError, IndexError):
            return 5, "parse error — default 5"
        except Exception as e:
            return 5, f"llm error: {str(e)[:80]}"

    def verify_catalog(
        self,
        catalog_path: Path,
        *,
        dry_run: bool = False,
        sleep_between: float = 0.1,
    ) -> Path:
        """
        Score every record in catalog["passed"] and write gemma_score/gemma_reason in-place.

        Returns catalog_path.
        """
        self.require_ollama()

        catalog = json.loads(catalog_path.read_text(encoding="utf-8"))
        records = catalog.get("passed", [])
        total = len(records)

        approved = dropped = 0
        print(f"[verifier] Scoring {total} records with {self.model} ...")

        for i, rec in enumerate(records, 1):
            score, reason = self.verify_record(rec)
            rec["gemma_score"] = score
            rec["gemma_reason"] = reason

            status = "PASS" if score >= self.min_pass_score else "DROP"
            if score >= self.min_pass_score:
                approved += 1
            else:
                dropped += 1

            print(f"  [{i:>4}/{total}] {status} {score:>2}/10  {rec['uid'][:22]:<24}  {reason[:55]}")

            if rec.get("record_type") not in self.auto_approve_types:
                time.sleep(sleep_between)

        print(f"\n[verifier] Approved={approved}  Dropped={dropped}")

        if not dry_run:
            tmp = catalog_path.with_suffix(".tmp.json")
            tmp.write_text(json.dumps(catalog, indent=2), encoding="utf-8")
            tmp.replace(catalog_path)
            print(f"[verifier] Updated -> {catalog_path}")

        return catalog_path

    def batch_verify(self, records: list[dict]) -> list[dict]:
        """Verify a list of record dicts in-place. Returns the list."""
        self.require_ollama()
        for rec in records:
            score, reason = self.verify_record(rec)
            rec["gemma_score"] = score
            rec["gemma_reason"] = reason
        return records
