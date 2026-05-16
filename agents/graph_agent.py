"""
graph_agent.py — Knowledge graph builder from Obsidian vault wikilinks.

Parses [[wikilinks]] from vault notes, builds a networkx graph, runs PageRank
and community detection, identifies hub nodes, and exports for visualization.

Usage:
    agent = GraphAgent(vault_dir=Path("C:/Users/advay/Obsidian/Research"))
    graph = agent.build()
    agent.print_stats(graph)
    agent.export_json(graph, Path("data/knowledge_graph.json"))

    # Find shortest path between topics:
    path = agent.shortest_path(graph, "PCNA", "GNN")

    # Get top hub nodes:
    hubs = agent.top_nodes(graph, n=10, metric="pagerank")
"""
from __future__ import annotations

import json
import re
import sys
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional


# ── graph dataclasses ─────────────────────────────────────────────────────────

@dataclass
class GraphNode:
    name: str
    path: Optional[Path] = None
    note_type: str = "unknown"   # from YAML frontmatter type:
    tags: list[str] = field(default_factory=list)
    word_count: int = 0
    has_frontmatter: bool = False
    pagerank: float = 0.0
    community: int = -1
    in_degree: int = 0
    out_degree: int = 0


@dataclass
class GraphEdge:
    source: str
    target: str
    weight: int = 1    # number of links from source → target


@dataclass
class KnowledgeGraph:
    nodes: dict[str, GraphNode]
    edges: list[GraphEdge]
    communities: dict[int, list[str]]
    stats: dict


# ── parsers ───────────────────────────────────────────────────────────────────

_WIKILINK_RE = re.compile(r"\[\[([^\]|#]+)(?:\|[^\]]*)?\]\]")
_FRONTMATTER_RE = re.compile(r"^---\s*\n(.*?)\n---", re.DOTALL)
_TYPE_RE = re.compile(r"^type:\s*(.+)$", re.MULTILINE)
_TAGS_RE = re.compile(r"^tags:\s*\[(.+)\]", re.MULTILINE)


def _parse_frontmatter(text: str) -> dict:
    m = _FRONTMATTER_RE.match(text)
    if not m:
        return {}
    block = m.group(1)
    result: dict = {"_has": True}
    tm = _TYPE_RE.search(block)
    if tm:
        result["type"] = tm.group(1).strip().strip('"')
    tgm = _TAGS_RE.search(block)
    if tgm:
        result["tags"] = [t.strip().strip('"') for t in tgm.group(1).split(",")]
    return result


def _extract_links(text: str) -> list[str]:
    return [m.group(1).strip() for m in _WIKILINK_RE.finditer(text)]


# ── graph agent ───────────────────────────────────────────────────────────────

class GraphAgent:
    """
    Parses Obsidian vault wikilinks into a knowledge graph.

    Computes PageRank, Louvain-style community detection (pure Python,
    no community package required), hub node identification, and JSON export
    compatible with Obsidian Graph View and D3.js force-directed layouts.
    """

    def __init__(
        self,
        vault_dir: Path,
        exclude_dirs: Optional[list[str]] = None,
        min_connections: int = 1,
    ) -> None:
        self.vault_dir = Path(vault_dir)
        self.exclude_dirs = set(exclude_dirs or [".obsidian", ".trash", "templates", "Templates"])
        self.min_connections = min_connections

    # ── build ─────────────────────────────────────────────────────────────────

    def build(self) -> KnowledgeGraph:
        """Parse vault and build knowledge graph."""
        print(f"[graph] Scanning {self.vault_dir}...", file=sys.stderr)

        nodes: dict[str, GraphNode] = {}
        raw_edges: list[tuple[str, str]] = []

        for md_file in self.vault_dir.rglob("*.md"):
            if any(part in self.exclude_dirs for part in md_file.parts):
                continue
            try:
                text = md_file.read_text(encoding="utf-8", errors="ignore")
            except Exception:
                continue

            name = md_file.stem
            fm = _parse_frontmatter(text)
            links = _extract_links(text)

            nodes[name] = GraphNode(
                name=name,
                path=md_file,
                note_type=fm.get("type", "note"),
                tags=fm.get("tags", []),
                word_count=len(text.split()),
                has_frontmatter=fm.get("_has", False),
            )
            for target in links:
                if target != name:
                    raw_edges.append((name, target))

        # Add referenced-but-not-created nodes
        for src, tgt in raw_edges:
            if tgt not in nodes:
                nodes[tgt] = GraphNode(name=tgt, note_type="missing")

        print(f"[graph] {len(nodes)} nodes, {len(raw_edges)} raw links", file=sys.stderr)

        # Count edge weights
        edge_counts: Counter = Counter(raw_edges)
        edges = [GraphEdge(s, t, w) for (s, t), w in edge_counts.items()]

        # Degree counts
        for edge in edges:
            if edge.source in nodes:
                nodes[edge.source].out_degree += edge.weight
            if edge.target in nodes:
                nodes[edge.target].in_degree += edge.weight

        # Filter by min connections
        if self.min_connections > 1:
            connected = {n for n, node in nodes.items()
                         if node.in_degree + node.out_degree >= self.min_connections}
            nodes = {n: v for n, v in nodes.items() if n in connected}
            edges = [e for e in edges if e.source in nodes and e.target in nodes]

        # PageRank
        self._compute_pagerank(nodes, edges)

        # Community detection
        communities = self._detect_communities(nodes, edges)
        for comm_id, members in communities.items():
            for name in members:
                if name in nodes:
                    nodes[name].community = comm_id

        stats = {
            "total_nodes": len(nodes),
            "total_edges": len(edges),
            "n_communities": len(communities),
            "missing_notes": sum(1 for n in nodes.values() if n.note_type == "missing"),
            "hub_notes": sum(1 for n in nodes.values() if n.in_degree >= 5),
        }

        print(f"[graph] Done: {stats}", file=sys.stderr)
        return KnowledgeGraph(nodes=nodes, edges=edges, communities=communities, stats=stats)

    # ── algorithms ────────────────────────────────────────────────────────────

    def _compute_pagerank(
        self, nodes: dict[str, GraphNode], edges: list[GraphEdge],
        damping: float = 0.85, iterations: int = 50,
    ) -> None:
        n = len(nodes)
        if n == 0:
            return

        # Build adjacency
        out_edges: dict[str, list[tuple[str, int]]] = defaultdict(list)
        out_weight: dict[str, int] = defaultdict(int)
        for e in edges:
            if e.source in nodes and e.target in nodes:
                out_edges[e.source].append((e.target, e.weight))
                out_weight[e.source] += e.weight

        pr = {name: 1.0 / n for name in nodes}

        for _ in range(iterations):
            new_pr: dict[str, float] = {name: (1 - damping) / n for name in nodes}
            for src, targets in out_edges.items():
                total = out_weight[src]
                if total == 0:
                    continue
                for tgt, w in targets:
                    new_pr[tgt] += damping * pr[src] * (w / total)
            pr = new_pr

        for name, score in pr.items():
            nodes[name].pagerank = round(score, 6)

    def _detect_communities(
        self, nodes: dict[str, GraphNode], edges: list[GraphEdge]
    ) -> dict[int, list[str]]:
        """Simple label propagation community detection."""
        labels = {name: i for i, name in enumerate(nodes)}
        adj: dict[str, list[str]] = defaultdict(list)
        for e in edges:
            if e.source in nodes and e.target in nodes:
                adj[e.source].append(e.target)
                adj[e.target].append(e.source)

        node_list = list(nodes.keys())
        for _ in range(10):
            changed = False
            for name in node_list:
                neighbors = adj.get(name, [])
                if not neighbors:
                    continue
                neighbor_labels = [labels[nb] for nb in neighbors if nb in labels]
                if not neighbor_labels:
                    continue
                most_common = Counter(neighbor_labels).most_common(1)[0][0]
                if most_common != labels[name]:
                    labels[name] = most_common
                    changed = True
            if not changed:
                break

        # Renumber from 0
        label_map: dict[int, int] = {}
        communities: dict[int, list[str]] = defaultdict(list)
        counter = 0
        for name, label in labels.items():
            if label not in label_map:
                label_map[label] = counter
                counter += 1
            communities[label_map[label]].append(name)

        return dict(communities)

    # ── queries ───────────────────────────────────────────────────────────────

    def top_nodes(
        self,
        graph: KnowledgeGraph,
        n: int = 10,
        metric: str = "pagerank",  # "pagerank" | "in_degree" | "out_degree"
    ) -> list[GraphNode]:
        key = {"pagerank": lambda x: x.pagerank, "in_degree": lambda x: x.in_degree, "out_degree": lambda x: x.out_degree}.get(metric, lambda x: x.pagerank)
        return sorted(graph.nodes.values(), key=key, reverse=True)[:n]

    def shortest_path(self, graph: KnowledgeGraph, source: str, target: str) -> list[str]:
        """BFS shortest path between two nodes."""
        if source not in graph.nodes or target not in graph.nodes:
            return []
        adj: dict[str, set[str]] = defaultdict(set)
        for e in graph.edges:
            adj[e.source].add(e.target)
            adj[e.target].add(e.source)

        from collections import deque
        queue: deque = deque([[source]])
        visited = {source}
        while queue:
            path = queue.popleft()
            node = path[-1]
            if node == target:
                return path
            for nb in adj.get(node, []):
                if nb not in visited:
                    visited.add(nb)
                    queue.append(path + [nb])
        return []

    def find_by_community(self, graph: KnowledgeGraph, community_id: int) -> list[GraphNode]:
        return [n for n in graph.nodes.values() if n.community == community_id]

    # ── output ────────────────────────────────────────────────────────────────

    def print_stats(self, graph: KnowledgeGraph) -> None:
        print(f"\n{'='*60}")
        print(f"  Knowledge Graph Stats")
        print(f"{'='*60}")
        for k, v in graph.stats.items():
            print(f"  {k:<22} {v}")
        print(f"\n  Top 10 nodes by PageRank:")
        for node in self.top_nodes(graph, n=10, metric="pagerank"):
            print(f"    [{node.community:>3}] {node.name:<35} PR={node.pagerank:.5f}  in={node.in_degree}")
        print(f"\n  Top communities by size:")
        for comm_id, members in sorted(graph.communities.items(), key=lambda x: -len(x[1]))[:5]:
            print(f"    Community {comm_id}: {len(members)} nodes — {', '.join(members[:5])}")
        print(f"{'='*60}")

    def export_json(self, graph: KnowledgeGraph, out_path: Path) -> Path:
        """Export D3.js-compatible JSON for force-directed visualization."""
        out_path = Path(out_path)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        data = {
            "stats": graph.stats,
            "nodes": [
                {
                    "id": name,
                    "type": node.note_type,
                    "pagerank": node.pagerank,
                    "community": node.community,
                    "in_degree": node.in_degree,
                    "out_degree": node.out_degree,
                    "word_count": node.word_count,
                    "tags": node.tags,
                }
                for name, node in graph.nodes.items()
            ],
            "links": [
                {"source": e.source, "target": e.target, "weight": e.weight}
                for e in graph.edges
            ],
        }
        out_path.write_text(json.dumps(data, indent=2), encoding="utf-8")
        print(f"[graph] Exported JSON → {out_path}")
        return out_path


def main() -> None:
    parser = argparse.ArgumentParser(description="Knowledge graph builder")
    parser.add_argument("vault", help="Obsidian vault directory")
    parser.add_argument("--output", default="data/graph.json", help="Output JSON path")
    parser.add_argument("--min-connections", type=int, default=1)
    parser.add_argument("--top", type=int, default=15, help="Top N nodes to print")

    import argparse
    args = parser.parse_args()

    agent = GraphAgent(vault_dir=Path(args.vault), min_connections=args.min_connections)
    graph = agent.build()
    agent.print_stats(graph)
    agent.export_json(graph, Path(args.output))


if __name__ == "__main__":
    main()
