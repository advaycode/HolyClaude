"""
knowledge_writer.py — Generic Obsidian knowledge graph writer.

Converts catalog records into structured Markdown notes and maintains an INDEX.md.
Works with any research domain — just provide template functions.

Usage:
    writer = KnowledgeWriter(vault_dir=Path("docs/knowledge"))
    writer.write_catalog(Path("data/catalog/catalog.json"))

    # Custom templates:
    writer = KnowledgeWriter(
        vault_dir=Path("my_vault"),
        templates={"paper": my_paper_template, "dataset": my_dataset_template},
    )
"""
from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable, Optional


# ── helpers ───────────────────────────────────────────────────────────────────

def _slug(uid: str) -> str:
    return re.sub(r"[^A-Za-z0-9_\-]", "_", uid)[:60]


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


# ── default templates ─────────────────────────────────────────────────────────

def _default_article_template(rec: dict) -> str:
    uid = rec.get("uid", "")
    title = rec.get("title", "") or uid
    source = rec.get("source", "")
    url = rec.get("url", "")
    desc = (rec.get("description") or "")[:500]
    relevance = rec.get("relevance", 0.0)
    gemma = rec.get("gemma_score", "N/A")
    g_reason = rec.get("gemma_reason", "")
    meta = rec.get("metadata", {})

    return f"""\
---
type: article
uid: {uid}
source: {source}
relevance_score: {relevance:.3f}
gemma_score: {gemma}
auto_indexed: {_now()}
---

# {title}

| Field | Value |
|---|---|
| Source | {source} |
| Relevance | {relevance:.3f} |
| Gemma score | {gemma}/10 |
| Gemma verdict | {g_reason} |

## Summary

{desc}

## URL

[Open]({url})

## Actions

- [ ] Read and assess
- [ ] Extract key findings to INDEX

## Links

[[INDEX]]
"""


def _default_dataset_template(rec: dict) -> str:
    uid = rec.get("uid", "")
    title = rec.get("title", "") or uid
    source = rec.get("source", "")
    url = rec.get("url", "")
    dl_url = rec.get("download_url", "")
    desc = (rec.get("description") or "")[:400]
    relevance = rec.get("relevance", 0.0)
    gemma = rec.get("gemma_score", "N/A")
    g_reason = rec.get("gemma_reason", "")

    return f"""\
---
type: dataset
uid: {uid}
source: {source}
relevance_score: {relevance:.3f}
gemma_score: {gemma}
auto_indexed: {_now()}
---

# {title}

| Field | Value |
|---|---|
| Source | {source} |
| Relevance | {relevance:.3f} |
| Gemma score | {gemma}/10 |
| Gemma verdict | {g_reason} |

## Description

{desc}

## Access

[Page]({url})
{f'[Download]({dl_url})' if dl_url else ''}

## Links

[[INDEX]]
"""


def _default_preprint_template(rec: dict) -> str:
    uid = rec.get("uid", "")
    title = rec.get("title", "") or uid
    url = rec.get("url", "")
    dl_url = rec.get("download_url", "")
    desc = (rec.get("description") or "")[:500]
    meta = rec.get("metadata", {})
    arxiv_id = meta.get("arxiv_id", "")

    return f"""\
---
type: preprint
uid: {uid}
arxiv_id: {arxiv_id}
auto_indexed: {_now()}
---

# {title}

## Abstract

{desc}

## Links

[Abstract]({url})
{f'[PDF]({dl_url})' if dl_url else ''}

[[INDEX]]
"""


DEFAULT_TEMPLATES: dict[str, Callable[[dict], str]] = {
    "article": _default_article_template,
    "paper": _default_article_template,
    "preprint": _default_preprint_template,
    "dataset": _default_dataset_template,
    "compound": _default_dataset_template,
    "code": _default_dataset_template,
}

# record_type -> subdir in vault
DEFAULT_SUBDIRS: dict[str, str] = {
    "article": "literature",
    "paper": "literature",
    "preprint": "preprints",
    "dataset": "datasets",
    "compound": "datasets",
    "code": "datasets",
    "structure": "structures",
}


# ── writer ─────────────────────────────────────────────────────────────────────

class KnowledgeWriter:
    """
    Writes Obsidian-compatible Markdown notes from catalog records.

    File layout:
        vault_dir/
          INDEX.md          — auto-updated wikilink index
          literature/       — articles, papers
          preprints/        — arXiv, bioRxiv
          datasets/         — Zenodo, GitHub releases
          structures/       — PDB, AlphaFold
    """

    def __init__(
        self,
        vault_dir: Path,
        templates: Optional[dict[str, Callable[[dict], str]]] = None,
        subdirs: Optional[dict[str, str]] = None,
        min_gemma: int = 6,
        auto_approve_types: Optional[list[str]] = None,
    ) -> None:
        self.vault_dir = Path(vault_dir)
        self.templates = {**DEFAULT_TEMPLATES, **(templates or {})}
        self.subdirs = {**DEFAULT_SUBDIRS, **(subdirs or {})}
        self.min_gemma = min_gemma
        self.auto_approve_types = set(auto_approve_types or ["structure", "pdb_structure"])

    def _should_write(self, rec: dict) -> bool:
        rtype = rec.get("record_type", "")
        if rtype in self.auto_approve_types:
            return True
        score = rec.get("gemma_score")
        return score is not None and score >= self.min_gemma

    def write_record(self, rec: dict, *, dry_run: bool = False) -> Optional[Path]:
        rtype = rec.get("record_type", "")
        uid = rec.get("uid", "unknown")

        template_fn = self.templates.get(rtype, _default_article_template)
        subdir = self.subdirs.get(rtype, "misc")
        content = template_fn(rec)

        out_dir = self.vault_dir / subdir
        out_path = out_dir / f"{_slug(uid)}.md"

        if not dry_run:
            out_dir.mkdir(parents=True, exist_ok=True)
            if not out_path.exists():
                out_path.write_text(content, encoding="utf-8")

        return out_path

    def write_catalog(
        self,
        catalog_path: Path,
        *,
        dry_run: bool = False,
    ) -> None:
        catalog = json.loads(catalog_path.read_text(encoding="utf-8"))
        records = catalog.get("passed", [])

        written: list[Path] = []
        skipped = 0

        print(f"[writer] Processing {len(records)} records (min_gemma={self.min_gemma})")

        for rec in records:
            if not self._should_write(rec):
                skipped += 1
                continue
            path = self.write_record(rec, dry_run=dry_run)
            if path:
                tag = "DRY" if dry_run else "WRITE"
                print(f"  [{tag}] {path.relative_to(self.vault_dir)}")
                written.append(path)

        self._update_index(written, dry_run=dry_run)
        print(f"\n[writer] Written={len(written)}  Skipped={skipped}")
        if dry_run:
            print("  (dry-run — no files modified)")

    def _update_index(self, new_paths: list[Path], *, dry_run: bool = False) -> None:
        if not new_paths:
            return
        index_path = self.vault_dir / "INDEX.md"
        existing = index_path.read_text(encoding="utf-8") if index_path.exists() else "# INDEX\n\n"

        section = "## Auto-Indexed"
        links = [f"- [[{p.stem}]]" for p in new_paths]

        if section not in existing:
            updated = existing + f"\n\n{section}\n\n" + "\n".join(links) + "\n"
        else:
            existing_links = set(existing.split(section)[-1].splitlines())
            new_links = [l for l in links if l.strip() not in existing_links]
            if not new_links:
                return
            updated = existing.replace(section, section + "\n" + "\n".join(new_links) + "\n", 1)

        if not dry_run:
            self.vault_dir.mkdir(parents=True, exist_ok=True)
            index_path.write_text(updated, encoding="utf-8")

    def add_template(self, record_type: str, fn: Callable[[dict], str]) -> None:
        self.templates[record_type] = fn

    def add_subdir(self, record_type: str, subdir: str) -> None:
        self.subdirs[record_type] = subdir
