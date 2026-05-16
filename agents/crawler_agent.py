"""
crawler_agent.py — Generic multi-source parallel web crawler with 5-layer validation.

Generalized from GNN-PCNA's pcna_crawler.py. Drop-in for any research domain.

Usage:
    crawler = CrawlerAgent(
        topic="PCNA cryptic pocket",
        sources=["pubmed", "biorxiv", "github"],
        output_dir=Path("data/catalog"),
    )
    catalog = crawler.run()

    # Or extend with custom sources:
    class MySource(BaseSource):
        name = "my_db"
        def fetch_all(self) -> list[SourceRecord]: ...

    crawler.register_source(MySource)
"""
from __future__ import annotations

import hashlib
import json
import re
import time
import urllib.parse
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

import requests

# ── constants ─────────────────────────────────────────────────────────────────

POLITE_DELAY = 0.35
MAX_RETRIES = 3
BACKOFF_BASE = 1.5

SESSION = requests.Session()
SESSION.headers.update({
    "User-Agent": "HolyClaude-research/1.0 (academic; advay.awesomer@gmail.com)"
})


# ── rate limiter ──────────────────────────────────────────────────────────────

class RateLimiter:
    def __init__(self) -> None:
        self._last: dict[str, float] = defaultdict(float)

    def wait(self, domain: str, delay: float = POLITE_DELAY) -> None:
        elapsed = time.monotonic() - self._last[domain]
        if elapsed < delay:
            time.sleep(delay - elapsed)
        self._last[domain] = time.monotonic()


_rate = RateLimiter()


# ── shared fetch ──────────────────────────────────────────────────────────────

def fetch(
    url: str,
    domain: str = "",
    *,
    method: str = "GET",
    json_body: Any = None,
    timeout: int = 20,
    rate_delay: float = POLITE_DELAY,
    headers: Optional[dict] = None,
) -> Optional[requests.Response]:
    """HTTP fetch with rate limiting and exponential-backoff retry."""
    _rate.wait(domain or urllib.parse.urlparse(url).netloc, rate_delay)
    for attempt in range(MAX_RETRIES):
        try:
            if method == "POST":
                r = SESSION.post(url, json=json_body, timeout=timeout, headers=headers)
            else:
                r = SESSION.get(url, timeout=timeout, headers=headers)
            if r.status_code == 429:
                wait = int(r.headers.get("Retry-After", 5))
                time.sleep(wait)
                continue
            r.raise_for_status()
            return r
        except requests.RequestException:
            if attempt == MAX_RETRIES - 1:
                return None
            time.sleep(BACKOFF_BASE ** attempt)
    return None


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


# ── record ────────────────────────────────────────────────────────────────────

@dataclass
class SourceRecord:
    uid: str
    record_type: str          # "article" | "dataset" | "code" | "structure" | "preprint"
    source: str
    url: str
    title: str = ""
    description: str = ""
    metadata: dict = field(default_factory=dict)
    download_url: str = ""
    validation: dict = field(default_factory=dict)
    passed: bool = False
    relevance: float = 0.0
    checksum: str = ""
    fetched_at: str = ""
    gemma_score: int = 0
    gemma_reason: str = ""

    def to_dict(self) -> dict:
        return asdict(self)


# ── validation pipeline ───────────────────────────────────────────────────────

class ValidationPipeline:
    """
    5-layer validation. Parameterized by topic keywords and domain-specific rules.

    Layers:
      L1 Network    — HTTP 200, content-type, min size
      L2 Format     — schema check for record_type
      L3 Content    — domain-specific checks (override l3_content for specialization)
      L4 Relevance  — keyword matching + source quality scoring
      L5 Provenance — SHA256 deduplication + audit trail
    """

    def __init__(
        self,
        keywords: list[str],
        min_relevance: float = 0.10,
        source_weights: dict[str, float] | None = None,
    ) -> None:
        self.keywords = [k.lower() for k in keywords]
        self.min_relevance = min_relevance
        self.source_weights: dict[str, float] = source_weights or {}

    # L1
    def l1_network(self, rec: SourceRecord, content: bytes, content_type: str, status: int) -> bool:
        result: dict = {"status_code": status, "content_type": content_type, "size_bytes": len(content)}
        if status != 200:
            result["fail"] = f"HTTP {status}"
            rec.validation["l1"] = result
            return False
        if len(content) < 200:
            result["fail"] = f"too small ({len(content)}B)"
            rec.validation["l1"] = result
            return False
        result["ok"] = True
        rec.validation["l1"] = result
        return True

    # L2
    def l2_format(self, rec: SourceRecord, content: bytes) -> bool:
        result: dict = {}
        text = content.decode("utf-8", errors="ignore")
        if rec.record_type in ("article", "preprint", "paper"):
            if len(text) < 100:
                result["fail"] = "text too short"
                rec.validation["l2"] = result
                return False
        elif rec.record_type == "dataset" and rec.url.endswith(".json"):
            try:
                json.loads(content)
            except json.JSONDecodeError as e:
                result["fail"] = f"invalid JSON: {e}"
                rec.validation["l2"] = result
                return False
        result["ok"] = True
        rec.validation["l2"] = result
        return True

    # L3 — override this for domain-specific validation
    def l3_content(self, rec: SourceRecord, content: bytes) -> bool:
        rec.validation["l3"] = {"ok": True, "skipped": "no domain-specific rules"}
        return True

    # L4
    def l4_relevance(self, rec: SourceRecord) -> float:
        result: dict = {}
        score = 0.0
        reasons: list[str] = []
        text = (rec.title + " " + rec.description).lower()
        kw_hits = [kw for kw in self.keywords if kw in text]
        if kw_hits:
            score += min(0.6, len(kw_hits) * 0.15)
            reasons.append(f"kw: {kw_hits[:3]}")
        score += self.source_weights.get(rec.source.split(":")[0], 0.0)
        score = min(score, 1.0)
        result["score"] = round(score, 3)
        result["reason"] = "; ".join(reasons) if reasons else "no match"
        rec.validation["l4"] = result
        rec.relevance = score
        return score

    # L5
    def l5_provenance(self, rec: SourceRecord, content: bytes, seen: set[str]) -> bool:
        result: dict = {}
        chk = sha256(content)
        if chk in seen:
            result["fail"] = "duplicate (same checksum)"
            rec.validation["l5"] = result
            return False
        seen.add(chk)
        rec.checksum = chk
        rec.fetched_at = datetime.now(timezone.utc).isoformat()
        result["sha256"] = chk
        result["ok"] = True
        rec.validation["l5"] = result
        return True

    def run(self, rec: SourceRecord, content: bytes, content_type: str, status: int, seen: set[str]) -> bool:
        if not self.l1_network(rec, content, content_type, status):
            return False
        if not self.l2_format(rec, content):
            return False
        if not self.l3_content(rec, content):
            return False
        rel = self.l4_relevance(rec)
        if rel < self.min_relevance:
            rec.validation["l4"]["fail"] = f"relevance {rel:.2f} < {self.min_relevance}"
            return False
        if not self.l5_provenance(rec, content, seen):
            return False
        rec.passed = True
        return True


# ── base source ───────────────────────────────────────────────────────────────

class BaseSource:
    name = "base"
    rate_delay = POLITE_DELAY

    def fetch_all(self) -> list[SourceRecord]:
        raise NotImplementedError

    def _get(self, url: str, **kw) -> Optional[requests.Response]:
        return fetch(url, self.name, rate_delay=self.rate_delay, **kw)

    def _post(self, url: str, body: Any, **kw) -> Optional[requests.Response]:
        return fetch(url, self.name, method="POST", json_body=body,
                     rate_delay=self.rate_delay, **kw)

    def _record(self, uid: str, rtype: str, url: str, **kw) -> SourceRecord:
        return SourceRecord(uid=uid, record_type=rtype, source=self.name, url=url, **kw)


# ── built-in generic sources ──────────────────────────────────────────────────

class PubMedSource(BaseSource):
    """PubMed full-text search for any topic."""
    name = "pubmed"

    def __init__(self, queries: list[str], max_per_query: int = 10) -> None:
        self.queries = queries
        self.max_per_query = max_per_query

    def fetch_all(self) -> list[SourceRecord]:
        records: list[SourceRecord] = []
        seen: set[str] = set()
        for q in self.queries:
            params = {"db": "pubmed", "term": q, "retmax": self.max_per_query, "retmode": "json"}
            r = self._get("https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi?" + urllib.parse.urlencode(params))
            if not r:
                continue
            try:
                for pmid in r.json()["esearchresult"]["idlist"]:
                    if pmid in seen:
                        continue
                    seen.add(pmid)
                    records.append(self._record(
                        f"PMID:{pmid}", "article",
                        f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/",
                        description=q, metadata={"pmid": pmid, "query": q},
                    ))
            except Exception:
                continue
        print(f"  [{self.name}] {len(records)} papers")
        return records


class ArXivSource(BaseSource):
    """arXiv preprint search."""
    name = "arxiv"

    def __init__(self, query: str, max_results: int = 20) -> None:
        self.query = query
        self.max_results = max_results

    def fetch_all(self) -> list[SourceRecord]:
        url = (
            f"http://export.arxiv.org/api/query?"
            f"search_query=all:{urllib.parse.quote(self.query)}"
            f"&max_results={self.max_results}&sortBy=relevance"
        )
        r = self._get(url)
        if not r:
            return []
        try:
            import xml.etree.ElementTree as ET
            ns = {"atom": "http://www.w3.org/2005/Atom"}
            root = ET.fromstring(r.text)
            records: list[SourceRecord] = []
            for entry in root.findall("atom:entry", ns):
                arxiv_id = (entry.findtext("atom:id", namespaces=ns) or "").split("/abs/")[-1]
                title = (entry.findtext("atom:title", namespaces=ns) or "").strip()
                summary = (entry.findtext("atom:summary", namespaces=ns) or "").strip()[:300]
                records.append(self._record(
                    f"arxiv:{arxiv_id}", "preprint",
                    f"https://arxiv.org/abs/{arxiv_id}",
                    title=title, description=summary,
                    download_url=f"https://arxiv.org/pdf/{arxiv_id}.pdf",
                    metadata={"arxiv_id": arxiv_id, "query": self.query},
                ))
            print(f"  [{self.name}] {len(records)} preprints")
            return records
        except Exception as e:
            print(f"  [{self.name}] error: {e}")
            return []


class GitHubSource(BaseSource):
    """Crawl GitHub repos for datasets and supplementary files."""
    name = "github"

    def __init__(self, repos: list[tuple[str, str, str]]) -> None:
        # repos: [(org, repo, description), ...]
        self.repos = repos

    def fetch_all(self) -> list[SourceRecord]:
        records: list[SourceRecord] = []
        for org, repo, desc in self.repos:
            api_url = f"https://api.github.com/repos/{org}/{repo}"
            r = self._get(f"{api_url}/releases")
            if r:
                try:
                    for rel in r.json()[:3]:
                        for asset in rel.get("assets", []):
                            records.append(self._record(
                                f"gh:{org}/{repo}/{asset['name']}", "dataset",
                                asset["browser_download_url"],
                                title=f"{repo}: {asset['name']}",
                                description=desc,
                                download_url=asset["browser_download_url"],
                                metadata={"repo": f"{org}/{repo}", "source": "github"},
                            ))
                except Exception:
                    pass
        print(f"  [{self.name}] {len(records)} releases found")
        return records


class ZenodoSource(BaseSource):
    """Zenodo dataset search."""
    name = "zenodo"

    def __init__(self, queries: list[str], max_per_query: int = 10) -> None:
        self.queries = queries
        self.max_per_query = max_per_query

    def fetch_all(self) -> list[SourceRecord]:
        records: list[SourceRecord] = []
        seen: set[str] = set()
        for q in self.queries:
            r = self._get(
                f"https://zenodo.org/api/records?"
                f"q={urllib.parse.quote(q)}&size={self.max_per_query}&sort=mostrecent"
            )
            if not r:
                continue
            try:
                for hit in r.json().get("hits", {}).get("hits", []):
                    doi = hit.get("doi", str(hit.get("id", "")))
                    if doi in seen:
                        continue
                    seen.add(doi)
                    files = hit.get("files", [])
                    dl = files[0].get("links", {}).get("self", "") if files else ""
                    records.append(self._record(
                        doi, "dataset",
                        hit.get("links", {}).get("html", ""),
                        title=hit.get("metadata", {}).get("title", ""),
                        description=(hit.get("metadata", {}).get("description") or "")[:200],
                        download_url=dl,
                        metadata={"doi": doi, "query": q},
                    ))
            except Exception:
                continue
        print(f"  [{self.name}] {len(records)} datasets")
        return records


# ── orchestrator ──────────────────────────────────────────────────────────────

class CrawlerAgent:
    """
    Generic multi-source parallel crawler with 5-layer validation.

    Example:
        agent = CrawlerAgent(
            topic="protein folding GNN",
            keywords=["protein folding", "graph neural network", "alphafold"],
            output_dir=Path("data/research"),
        )
        agent.add_source(PubMedSource(["protein folding GNN", "AlphaFold binding site"]))
        agent.add_source(ArXivSource("protein folding graph neural network"))
        catalog = agent.run()
    """

    def __init__(
        self,
        topic: str,
        keywords: list[str],
        output_dir: Path,
        workers: int = 6,
        min_relevance: float = 0.10,
        source_weights: dict[str, float] | None = None,
    ) -> None:
        self.topic = topic
        self.output_dir = Path(output_dir)
        self.workers = workers
        self.pipeline = ValidationPipeline(keywords, min_relevance, source_weights)
        self._sources: list[BaseSource] = []
        self._seen_checksums: set[str] = set()
        self._seen_uids: set[str] = set()

    def add_source(self, source: BaseSource) -> None:
        self._sources.append(source)

    def register_source(self, source: BaseSource) -> None:
        self.add_source(source)

    def run(self) -> dict:
        """Crawl all sources, validate, save catalog. Returns catalog dict."""
        print(f"\n=== CrawlerAgent: {self.topic} ===")
        print(f"Sources: {[s.name for s in self._sources]}  Workers: {self.workers}\n")

        all_records: list[SourceRecord] = []
        with ThreadPoolExecutor(max_workers=self.workers) as ex:
            futures = {ex.submit(src.fetch_all): src.name for src in self._sources}
            for future in as_completed(futures):
                try:
                    all_records.extend(future.result())
                except Exception as e:
                    print(f"  [!] {futures[future]}: {e}")

        print(f"\nCollected: {len(all_records)} records")

        # Dedup by UID
        deduped = [r for r in all_records if not (r.uid in self._seen_uids or self._seen_uids.add(r.uid))]
        print(f"After dedup: {len(deduped)}")

        passed: list[SourceRecord] = []
        failed: list[SourceRecord] = []

        for i, rec in enumerate(deduped, 1):
            url = rec.download_url or rec.url
            r = fetch(url, rec.source, timeout=20)
            if r is None:
                rec.validation["l1"] = {"fail": "request failed"}
                failed.append(rec)
            else:
                ok = self.pipeline.run(rec, r.content, r.headers.get("Content-Type", ""), r.status_code, self._seen_checksums)
                (passed if ok else failed).append(rec)
            if i % 25 == 0:
                print(f"  validated {i}/{len(deduped)} — pass={len(passed)}")

        print(f"\nValidation: {len(passed)} passed / {len(failed)} failed")
        return self._save(passed, failed)

    def _save(self, passed: list[SourceRecord], failed: list[SourceRecord]) -> dict:
        self.output_dir.mkdir(parents=True, exist_ok=True)
        now = datetime.now(timezone.utc).isoformat()

        catalog = {
            "generated_at": now,
            "topic": self.topic,
            "stats": {
                "passed": len(passed),
                "failed": len(failed),
                "by_type": dict(
                    (rtype, sum(1 for r in passed if r.record_type == rtype))
                    for rtype in set(r.record_type for r in passed)
                ),
                "by_source": dict(
                    sorted(
                        ((src, sum(1 for r in passed if r.source == src))
                         for src in set(r.source for r in passed)),
                        key=lambda x: -x[1],
                    )
                ),
            },
            "passed": sorted([r.to_dict() for r in passed], key=lambda x: -x.get("relevance", 0)),
            "failed_summary": [
                {"uid": r.uid, "source": r.source,
                 "reason": next((v["fail"] for v in r.validation.values() if isinstance(v, dict) and "fail" in v), "?")}
                for r in failed
            ],
        }

        out = self.output_dir / "catalog.json"
        out.write_text(json.dumps(catalog, indent=2), encoding="utf-8")
        print(f"Catalog saved: {out}")
        return catalog
