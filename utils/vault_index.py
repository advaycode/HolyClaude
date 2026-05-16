"""
vault_index.py — Fast TF-IDF search index for Obsidian vaults.

Builds an incremental TF-IDF index from vault notes. Supports cosine similarity
search, frontmatter tag filtering, type filtering, and mtime-aware updates
(only re-indexes changed files).

Usage:
    idx = VaultIndex(vault_dir=Path("C:/Users/advay/Obsidian"))
    idx.build()   # or idx.load() if previously saved
    idx.save()

    results = idx.search("PCNA cryptic pocket GNN", n=5)
    for r in results:
        print(f"{r.score:.3f}  {r.note_name}  [{r.note_type}]")
        print(r.snippet)

    # Filter by type:
    results = idx.search("AlphaFold", note_type="article")
"""
from __future__ import annotations

import json
import math
import pickle
import re
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Optional


@dataclass
class SearchResult:
    note_name: str
    note_path: str
    score: float
    snippet: str
    note_type: str = "note"
    tags: list[str] = None

    def __post_init__(self):
        if self.tags is None:
            self.tags = []


# ── text processing ───────────────────────────────────────────────────────────

_STOP_WORDS = {
    "the","a","an","and","or","but","in","on","at","to","for","of","with",
    "by","from","is","are","was","were","be","been","being","have","has",
    "had","do","does","did","will","would","could","should","may","might",
    "this","that","these","those","it","its","we","you","he","she","they",
    "not","no","nor","as","if","then","than","so","yet","both","either",
}

_WIKILINK_RE = re.compile(r"\[\[([^\]]+)\]\]")
_FRONTMATTER_RE = re.compile(r"^---\s*\n(.*?)\n---\s*\n", re.DOTALL)
_TAG_RE = re.compile(r"^tags:\s*[\[\s]([^\]\n]+)", re.MULTILINE)
_TYPE_RE = re.compile(r"^type:\s*(.+)$", re.MULTILINE)


def _tokenize(text: str) -> list[str]:
    text = _WIKILINK_RE.sub(r"\1", text)
    text = re.sub(r"[^\w\s]", " ", text.lower())
    return [w for w in text.split() if w not in _STOP_WORDS and len(w) >= 3]


def _extract_meta(text: str) -> tuple[str, list[str]]:
    m = _FRONTMATTER_RE.match(text)
    note_type, tags = "note", []
    if m:
        block = m.group(1)
        tm = _TYPE_RE.search(block)
        if tm:
            note_type = tm.group(1).strip().strip('"')
        tgm = _TAG_RE.search(block)
        if tgm:
            tags = [t.strip().strip('"') for t in re.split(r"[,\s]+", tgm.group(1)) if t.strip()]
    return note_type, tags


def _snippet(text: str, query_terms: list[str], chars: int = 200) -> str:
    text_clean = _FRONTMATTER_RE.sub("", text).strip()
    lower = text_clean.lower()
    best_pos = 0
    best_score = 0
    for i in range(0, max(1, len(lower) - chars), 50):
        window = lower[i:i+chars]
        score = sum(1 for t in query_terms if t in window)
        if score > best_score:
            best_score, best_pos = score, i
    snippet = text_clean[best_pos:best_pos+chars].strip()
    return snippet.replace("\n", " ")


# ── vault index ───────────────────────────────────────────────────────────────

class VaultIndex:
    """
    Incremental TF-IDF search index for Obsidian vaults.

    - Tokenizes note text + wikilinks, strips stop words
    - IDF computed over corpus, TF normalized per document
    - Cosine similarity with query vector
    - Saves/loads from pickle for fast startup
    - mtime-based incremental update: only re-indexes changed files
    """

    INDEX_VERSION = 2

    def __init__(
        self,
        vault_dir: Path,
        exclude_dirs: Optional[list[str]] = None,
        index_path: Optional[Path] = None,
    ) -> None:
        self.vault_dir = Path(vault_dir)
        self.exclude_dirs = set(exclude_dirs or [".obsidian", ".trash", "templates", "Templates", "_archive"])
        self.index_path = index_path or (self.vault_dir / ".index" / "holy_index.pkl")

        # Index state
        self._tf: dict[str, dict[str, float]] = {}        # doc_id → {term: tf}
        self._idf: dict[str, float] = {}                  # term → idf
        self._meta: dict[str, dict] = {}                  # doc_id → {path, type, tags, mtime}
        self._doc_texts: dict[str, str] = {}              # doc_id → raw text (for snippets)
        self._built = False

    # ── build / update ────────────────────────────────────────────────────────

    def build(self, force: bool = False) -> "VaultIndex":
        """Build or incrementally update the index."""
        t0 = time.monotonic()

        md_files = [
            f for f in self.vault_dir.rglob("*.md")
            if not any(part in self.exclude_dirs for part in f.parts)
        ]

        updated = 0
        for md_file in md_files:
            doc_id = md_file.stem
            mtime = md_file.stat().st_mtime

            if not force and doc_id in self._meta and self._meta[doc_id].get("mtime") == mtime:
                continue  # unchanged

            try:
                text = md_file.read_text(encoding="utf-8", errors="ignore")
            except Exception:
                continue

            note_type, tags = _extract_meta(text)
            tokens = _tokenize(text)
            if not tokens:
                continue

            tf_raw: dict[str, int] = {}
            for tok in tokens:
                tf_raw[tok] = tf_raw.get(tok, 0) + 1

            n = len(tokens)
            self._tf[doc_id] = {t: c / n for t, c in tf_raw.items()}
            self._meta[doc_id] = {"path": str(md_file), "type": note_type, "tags": tags, "mtime": mtime}
            self._doc_texts[doc_id] = text
            updated += 1

        # Recompute IDF over all documents
        N = len(self._tf)
        df: dict[str, int] = {}
        for tf_map in self._tf.values():
            for term in tf_map:
                df[term] = df.get(term, 0) + 1
        self._idf = {t: math.log(N / d + 1) for t, d in df.items()}

        self._built = True
        elapsed = time.monotonic() - t0
        print(f"[vault_index] Indexed {len(self._tf)} notes ({updated} updated) in {elapsed:.2f}s")
        return self

    def save(self) -> Path:
        self.index_path.parent.mkdir(parents=True, exist_ok=True)
        with self.index_path.open("wb") as f:
            pickle.dump({
                "version": self.INDEX_VERSION,
                "tf": self._tf,
                "idf": self._idf,
                "meta": self._meta,
                "texts": self._doc_texts,
            }, f)
        return self.index_path

    def load(self) -> bool:
        if not self.index_path.exists():
            return False
        try:
            with self.index_path.open("rb") as f:
                data = pickle.load(f)
            if data.get("version") != self.INDEX_VERSION:
                return False
            self._tf = data["tf"]
            self._idf = data["idf"]
            self._meta = data["meta"]
            self._doc_texts = data.get("texts", {})
            self._built = True
            return True
        except Exception:
            return False

    def load_or_build(self) -> "VaultIndex":
        if not self.load():
            self.build()
            self.save()
        return self

    # ── search ────────────────────────────────────────────────────────────────

    def search(
        self,
        query: str,
        n: int = 5,
        note_type: Optional[str] = None,
        tags: Optional[list[str]] = None,
        min_score: float = 0.0,
    ) -> list[SearchResult]:
        if not self._built:
            raise RuntimeError("Index not built. Call build() or load_or_build() first.")

        query_terms = _tokenize(query)
        if not query_terms:
            return []

        # Query TF-IDF vector
        q_tf: dict[str, float] = {}
        for t in query_terms:
            q_tf[t] = q_tf.get(t, 0) + 1.0
        q_len = len(query_terms)
        q_vec = {t: (c / q_len) * self._idf.get(t, 0) for t, c in q_tf.items()}

        scores: list[tuple[float, str]] = []
        for doc_id, tf_map in self._tf.items():
            meta = self._meta.get(doc_id, {})
            if note_type and meta.get("type") != note_type:
                continue
            if tags:
                doc_tags = set(meta.get("tags", []))
                if not any(t in doc_tags for t in tags):
                    continue

            # Cosine similarity
            dot = sum(q_vec.get(t, 0) * tf_map.get(t, 0) * self._idf.get(t, 0)
                      for t in q_vec)
            doc_norm = math.sqrt(sum((v * self._idf.get(t, 0))**2 for t, v in tf_map.items()))
            q_norm = math.sqrt(sum(v**2 for v in q_vec.values()))
            if doc_norm * q_norm == 0:
                continue
            score = dot / (doc_norm * q_norm)
            if score > min_score:
                scores.append((score, doc_id))

        scores.sort(reverse=True)

        results = []
        for score, doc_id in scores[:n]:
            meta = self._meta[doc_id]
            text = self._doc_texts.get(doc_id, "")
            results.append(SearchResult(
                note_name=doc_id,
                note_path=meta["path"],
                score=round(score, 4),
                snippet=_snippet(text, query_terms),
                note_type=meta.get("type", "note"),
                tags=meta.get("tags", []),
            ))

        return results

    def stats(self) -> dict:
        return {
            "notes_indexed": len(self._tf),
            "unique_terms": len(self._idf),
            "vault_dir": str(self.vault_dir),
            "index_path": str(self.index_path),
        }
