"""
hub_writer.py — Knowledge graph hub writer with Dataview-compatible YAML frontmatter.

Generalized from GNN-PCNA's catalog_to_obsidian.py.
Creates a full wikilinked vault with hub notes and a master KNOWLEDGE_GRAPH.md.

Output structure:
    vault_dir/
      KNOWLEDGE_GRAPH.md     ← master hub (root node)
      _HUB_ARTICLES.md       ← hub linking all article notes
      _HUB_DATASETS.md
      _HUB_PREPRINTS.md
      articles/SLUG.md       ← one note per article
      datasets/SLUG.md
      preprints/SLUG.md

Usage:
    writer = HubWriter(vault_dir=Path("docs/vault"), project_name="GNN-PCNA")
    writer.write_catalog(Path("data/catalog/catalog.json"))

    # Extend with custom note templates:
    writer.add_type_handler("compound", _compound_template, subdir="compounds")
"""
from __future__ import annotations

import json
import re
import unicodedata
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Optional


# ── helpers ───────────────────────────────────────────────────────────────────

def slugify(s: str) -> str:
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode()
    s = re.sub(r"[^\w\s-]", "", s).strip()
    s = re.sub(r"[\s_]+", "_", s)
    return s[:80]


def yaml_str(v: Any) -> str:
    s = str(v or "").strip()
    if any(c in s for c in ':#{}[]|>&*!,"'):
        s = s.replace('"', '\\"')
        return f'"{s}"'
    return s or '""'


def relevance_label(r: float) -> str:
    if r >= 0.8: return "high"
    if r >= 0.5: return "medium"
    if r >= 0.2: return "low"
    return "minimal"


def _now_date() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


# ── default templates ─────────────────────────────────────────────────────────

def _article_template(rec: dict, project: str) -> str:
    uid = rec.get("uid", "")
    title = (rec.get("title") or uid)[:120]
    source = rec.get("source", "")
    url = rec.get("url", "")
    desc = (rec.get("description") or "")[:500]
    rel = rec.get("relevance", 0.0)
    gemma = rec.get("gemma_score", "N/A")
    g_reason = rec.get("gemma_reason", "")
    meta = rec.get("metadata", {})
    pmid = meta.get("pmid", "")

    return (
        f"---\n"
        f"type: article\n"
        f"uid: {yaml_str(uid)}\n"
        f"title: {yaml_str(title)}\n"
        f"source: {yaml_str(source)}\n"
        f"pmid: {pmid}\n"
        f"relevance: {round(rel, 3)}\n"
        f"relevance_label: {relevance_label(rel)}\n"
        f"gemma_score: {gemma}\n"
        f"project: {yaml_str(project)}\n"
        f"auto_indexed: {_now_date()}\n"
        f"---\n\n"
        f"# {title}\n\n"
        f"## Abstract\n\n{desc}\n\n"
        f"## Source\n\n"
        f"- **Database**: {source}\n"
        f"- **URL**: [{uid}]({url})\n"
        f"- **PMID**: {pmid or '—'}\n"
        f"- **Relevance**: {rel:.2f} ({relevance_label(rel)})\n"
        f"- **Gemma score**: {gemma}/10 — {g_reason}\n\n"
        f"## Action\n\n"
        f"- [ ] Read and assess\n"
        f"- [ ] Extract key findings\n"
        f"- [ ] Add to NotebookLM if relevant\n\n"
        f"## Links\n\n[[KNOWLEDGE_GRAPH]] · [[_HUB_ARTICLES]]\n"
    )


def _dataset_template(rec: dict, project: str) -> str:
    uid = rec.get("uid", "")
    title = (rec.get("title") or uid)[:120]
    source = rec.get("source", "")
    url = rec.get("url", "")
    dl = rec.get("download_url", "")
    desc = (rec.get("description") or "")[:400]
    rel = rec.get("relevance", 0.0)
    gemma = rec.get("gemma_score", "N/A")

    return (
        f"---\n"
        f"type: dataset\n"
        f"uid: {yaml_str(uid)}\n"
        f"title: {yaml_str(title)}\n"
        f"source: {yaml_str(source)}\n"
        f"relevance: {round(rel, 3)}\n"
        f"relevance_label: {relevance_label(rel)}\n"
        f"gemma_score: {gemma}\n"
        f"project: {yaml_str(project)}\n"
        f"auto_indexed: {_now_date()}\n"
        f"---\n\n"
        f"# {title}\n\n"
        f"## Description\n\n{desc}\n\n"
        f"## Access\n\n"
        f"[Page]({url})\n"
        + (f"[Download]({dl})\n" if dl else "")
        + f"\n## Links\n\n[[KNOWLEDGE_GRAPH]] · [[_HUB_DATASETS]]\n"
    )


def _preprint_template(rec: dict, project: str) -> str:
    uid = rec.get("uid", "")
    title = (rec.get("title") or uid)[:120]
    url = rec.get("url", "")
    dl = rec.get("download_url", "")
    desc = (rec.get("description") or "")[:500]
    rel = rec.get("relevance", 0.0)
    meta = rec.get("metadata", {})
    arxiv_id = meta.get("arxiv_id", "")

    return (
        f"---\n"
        f"type: preprint\n"
        f"uid: {yaml_str(uid)}\n"
        f"arxiv_id: {arxiv_id}\n"
        f"title: {yaml_str(title)}\n"
        f"relevance: {round(rel, 3)}\n"
        f"project: {yaml_str(project)}\n"
        f"auto_indexed: {_now_date()}\n"
        f"---\n\n"
        f"# {title}\n\n"
        f"## Abstract\n\n{desc}\n\n"
        f"[Abstract]({url})"
        + (f" · [PDF]({dl})" if dl else "")
        + f"\n\n## Links\n\n[[KNOWLEDGE_GRAPH]] · [[_HUB_PREPRINTS]]\n"
    )


# ── type registry ─────────────────────────────────────────────────────────────

DEFAULT_TYPES: dict[str, tuple[Callable, str]] = {
    "article": (_article_template, "articles"),
    "paper": (_article_template, "articles"),
    "preprint": (_preprint_template, "preprints"),
    "dataset": (_dataset_template, "datasets"),
    "compound": (_dataset_template, "compounds"),
    "code": (_dataset_template, "code"),
}

HUB_NAMES: dict[str, str] = {
    "articles": "ARTICLES",
    "preprints": "PREPRINTS",
    "datasets": "DATASETS",
    "compounds": "COMPOUNDS",
    "code": "CODE",
    "structures": "STRUCTURES",
}


# ── hub writer ────────────────────────────────────────────────────────────────

class HubWriter:
    """
    Writes a full Obsidian knowledge vault with hub notes from a catalog.

    Creates:
    - One note per record (sorted into subdirectories by type)
    - Hub notes linking all notes of each type (_HUB_TYPE.md)
    - Master KNOWLEDGE_GRAPH.md root node
    """

    def __init__(
        self,
        vault_dir: Path,
        project_name: str = "Research",
        type_handlers: Optional[dict[str, tuple[Callable, str]]] = None,
        min_gemma: int = 6,
        min_relevance: float = 0.0,
        auto_approve_types: Optional[list[str]] = None,
    ) -> None:
        self.vault_dir = Path(vault_dir)
        self.project_name = project_name
        self.type_handlers = {**DEFAULT_TYPES, **(type_handlers or {})}
        self.min_gemma = min_gemma
        self.min_relevance = min_relevance
        self.auto_approve_types = set(auto_approve_types or ["structure", "pdb_structure"])

    def add_type_handler(self, record_type: str, template_fn: Callable, subdir: str) -> None:
        self.type_handlers[record_type] = (template_fn, subdir)

    def _should_write(self, rec: dict) -> bool:
        if rec.get("record_type") in self.auto_approve_types:
            return True
        if rec.get("relevance", 0) < self.min_relevance:
            return False
        score = rec.get("gemma_score")
        if score is not None and score < self.min_gemma:
            return False
        return True

    def write_record(self, rec: dict, *, dry_run: bool = False) -> Optional[tuple[Path, str]]:
        rtype = rec.get("record_type", "")
        uid = rec.get("uid", "unknown")

        handler = self.type_handlers.get(rtype)
        if not handler:
            return None

        template_fn, subdir = handler
        content = template_fn(rec, self.project_name)
        out_dir = self.vault_dir / subdir
        out_path = out_dir / f"{slugify(uid)}.md"

        if not dry_run:
            out_dir.mkdir(parents=True, exist_ok=True)
            if not out_path.exists():
                out_path.write_text(content, encoding="utf-8")

        return out_path, subdir

    def write_hub(
        self,
        subdir: str,
        nodes: list[tuple[str, str, float]],
        description: str = "",
    ) -> Path:
        hub_key = HUB_NAMES.get(subdir, subdir.upper())
        fname = f"_HUB_{hub_key}.md"
        dest = self.vault_dir / fname

        nodes_sorted = sorted(nodes, key=lambda x: -x[2])
        high = [(u, t, r) for u, t, r in nodes_sorted if r >= 0.5]
        medium = [(u, t, r) for u, t, r in nodes_sorted if 0.2 <= r < 0.5]
        low = [(u, t, r) for u, t, r in nodes_sorted if r < 0.2]

        lines = [
            f"---\ntype: hub\nhub_for: {subdir}\ngenerated: {_now_date()}\ntotal_nodes: {len(nodes)}\n---\n",
            f"# {hub_key.title()} Hub\n",
            description or f"All {subdir} nodes in the {self.project_name} knowledge graph.",
            f"\n**{len(nodes)} nodes** | Updated: {_now_date()}",
            f"\n[[KNOWLEDGE_GRAPH]]\n",
        ]

        def _section(label: str, items: list):
            if not items:
                return
            lines.append(f"\n## {label} ({len(items)})\n")
            lines.append("| Node | Title | Relevance |")
            lines.append("|---|---|---|")
            for uid, title, rel in items:
                lines.append(f"| [[{uid}]] | {title[:60]} | {rel:.2f} |")

        _section("High Relevance", high)
        _section("Medium Relevance", medium)
        _section("Low / Peripheral", low)
        lines.append("\n## All\n")
        lines.append(" · ".join(f"[[{u}]]" for u, _, _ in nodes_sorted))

        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text("\n".join(lines), encoding="utf-8")
        return dest

    def write_knowledge_graph(self, stats: dict, extra_sections: str = "") -> Path:
        dest = self.vault_dir / "KNOWLEDGE_GRAPH.md"
        hub_rows = "\n".join(
            f"| [[_HUB_{HUB_NAMES.get(sd, sd.upper())}]] | {cnt} | {sd.title()} nodes |"
            for sd, cnt in stats.items() if sd != "total"
        )
        content = (
            f"---\ntype: knowledge-graph-root\ngenerated: {_now_date()}\n"
            f"total_nodes: {stats.get('total', 0)}\nproject: {yaml_str(self.project_name)}\n---\n\n"
            f"# {self.project_name} Knowledge Graph\n\n"
            f"> Root node. {stats.get('total', 0)} nodes indexed by HolyClaude.\n\n"
            f"**Generated**: {_now_date()}\n\n"
            f"## Hubs\n\n| Hub | Nodes | Description |\n|---|---|---|\n{hub_rows}\n\n"
            + extra_sections
        )
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(content, encoding="utf-8")
        return dest

    def write_catalog(self, catalog_path: Path, *, dry_run: bool = False) -> dict:
        catalog = json.loads(catalog_path.read_text(encoding="utf-8"))
        records = catalog.get("passed", catalog.get("all_records", []))
        print(f"[hub_writer] {len(records)} records → {self.vault_dir}")

        # subdir -> list of (uid, title, relevance)
        by_subdir: dict[str, list[tuple[str, str, float]]] = {}
        written = 0

        for rec in records:
            if not self._should_write(rec):
                continue
            result = self.write_record(rec, dry_run=dry_run)
            if result:
                path, subdir = result
                uid = rec.get("uid", path.stem)
                title = (rec.get("title") or uid)[:60]
                rel = rec.get("relevance", 0.0)
                by_subdir.setdefault(subdir, []).append((uid, title, rel))
                tag = "DRY" if dry_run else "WRITE"
                if written < 5 or written % 20 == 0:
                    print(f"  [{tag}] {subdir}/{path.name}")
                written += 1

        # Write hub notes
        for subdir, nodes in by_subdir.items():
            if not dry_run:
                self.write_hub(subdir, nodes)

        stats = {sd: len(nodes) for sd, nodes in by_subdir.items()}
        stats["total"] = sum(stats.values())

        if not dry_run:
            self.write_knowledge_graph(stats)

        print(f"[hub_writer] Written={written}  Hubs={list(by_subdir.keys())}")
        return stats
