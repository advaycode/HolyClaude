"""Parts catalog index over Advay's Inventor library (~13k files).

A fast metadata scan (path / name / part-number / size / mtime / project) powers
`search_parts` so the agent can find and reuse existing goBILDA / vendor / authored
parts instead of remodelling. An optional deep scan reads binaries for referenced
components and iLogic markers. Deep COM feature-tree extraction is Phase 4.
"""

from __future__ import annotations

import re
import sqlite3
from pathlib import Path
from typing import Optional

from .. import config

DB_PATH = config.WORK_DIR / "parts_index.db"

GOBILDA_RE = re.compile(r"\d{4}-\d{4}-\d{4}")
WCP_RE = re.compile(r"[A-Z]{2,4}\d{2,3}[A-Z]?-\d{3}-\d{3}")
DEFAULT_ROOTS = [str(Path(config.CAD_OUTPUT_DIR)), str(Path.home() / "Downloads")]
SKIP = ("\\OneDrive\\", "\\AppData\\", "\\.git\\", "\\OldVersions\\", "node_modules")


def _connect() -> sqlite3.Connection:
    config.ensure_work_dir()
    con = sqlite3.connect(DB_PATH)
    con.execute("""
        CREATE TABLE IF NOT EXISTS parts (
            path TEXT PRIMARY KEY, name TEXT, ext TEXT, part_number TEXT,
            project TEXT, kind TEXT, size INTEGER, mtime REAL,
            ilogic INTEGER DEFAULT 0, refs TEXT DEFAULT ''
        )""")
    con.execute("CREATE INDEX IF NOT EXISTS idx_name ON parts(name)")
    con.execute("CREATE INDEX IF NOT EXISTS idx_pn ON parts(part_number)")
    return con


def _project_of(path: Path) -> str:
    parts = path.parts
    for anchor in ("CacheCAD",):
        if anchor in parts:
            i = parts.index(anchor)
            if i + 1 < len(parts):
                return parts[i + 1]
    # else: first folder under Downloads / home
    try:
        rel = path.relative_to(Path.home())
        return rel.parts[0] if rel.parts else ""
    except Exception:
        return path.parts[-2] if len(path.parts) > 1 else ""


def _part_number(stem: str) -> str:
    for rx in (GOBILDA_RE, WCP_RE):
        m = rx.search(stem)
        if m:
            return m.group(0)
    return ""


def _deep_markers(path: Path) -> tuple[int, str]:
    """Cheap binary scan: iLogic presence + referenced .ipt/.iam names."""
    try:
        data = path.read_bytes()
    except Exception:
        return 0, ""
    ilogic = 1 if (b"iLogic" in data or b"Default.ivb" in data) else 0
    refs = sorted(set(re.findall(rb"[\w \-]{1,60}\.ip[t]", data)))[:40]
    ref_str = ";".join(r.decode("latin-1", "ignore") for r in refs)
    return ilogic, ref_str


def build_index(roots: Optional[list[str]] = None, deep: bool = False,
                limit: Optional[int] = None) -> dict:
    roots = roots or DEFAULT_ROOTS
    con = _connect()
    n = 0
    for root in roots:
        rp = Path(root)
        if not rp.exists():
            continue
        root_str = str(rp)
        for path in rp.rglob("*"):
            if path.suffix.lower() not in (".ipt", ".iam"):
                continue
            full = str(path)
            rel = full[len(root_str):]   # skip-filter only BELOW the root, so explicit roots work
            if any(s in rel for s in SKIP):
                continue
            try:
                st = path.stat()
            except Exception:
                continue
            ilogic, refs = (0, "")
            if deep:
                ilogic, refs = _deep_markers(path)
            con.execute(
                "INSERT OR REPLACE INTO parts VALUES (?,?,?,?,?,?,?,?,?,?)",
                (full, path.stem, path.suffix.lower()[1:], _part_number(path.stem),
                 _project_of(path), "assembly" if path.suffix.lower() == ".iam" else "part",
                 st.st_size, st.st_mtime, ilogic, refs))
            n += 1
            if limit and n >= limit:
                break
        if limit and n >= limit:
            break
    con.commit()
    con.close()
    return {"indexed": n, "deep": deep, "db": str(DB_PATH)}


def search(query: str, limit: int = 20) -> list[dict]:
    if not DB_PATH.exists():
        return []
    con = _connect()
    con.row_factory = sqlite3.Row
    like = f"%{query}%"
    rows = con.execute(
        """SELECT path,name,part_number,project,kind,size,mtime,ilogic FROM parts
           WHERE name LIKE ? OR part_number LIKE ? OR path LIKE ? OR project LIKE ?
           ORDER BY (part_number=? ) DESC, mtime DESC LIMIT ?""",
        (like, like, like, like, query, limit)).fetchall()
    con.close()
    return [dict(r) for r in rows]


def stats() -> dict:
    if not DB_PATH.exists():
        return {"indexed": 0}
    con = _connect()
    total = con.execute("SELECT COUNT(*) FROM parts").fetchone()[0]
    by_kind = dict(con.execute("SELECT kind, COUNT(*) FROM parts GROUP BY kind").fetchall())
    con.close()
    return {"indexed": total, "by_kind": by_kind, "db": str(DB_PATH)}
