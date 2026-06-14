"""Free web research (no API key, no cost) for build planning.

Uses robust JSON endpoints instead of fragile HTML scraping:
  * Wikipedia API  — plain-text article extracts (great for real-world objects:
    a fire engine's parts, an epicyclic gearbox's stages, etc.)
  * DuckDuckGo Instant Answer JSON — abstract + related topics as a fallback.

Returns concise text capped for the local model's context window.
"""

from __future__ import annotations

import json
import re
import urllib.parse
import urllib.request

# Wikipedia asks for a descriptive User-Agent; a generic browser UA can 403.
_UA = "CADCopilot/1.0 (local CAD build-planning research)"


def _get(url: str, timeout: int = 20) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": _UA})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        charset = r.headers.get_content_charset() or "utf-8"
        return r.read().decode(charset, "ignore")


def _json(url: str) -> dict:
    return json.loads(_get(url))


def _wiki(query: str, n: int = 2, per: int = 1800) -> list[str]:
    api = "https://en.wikipedia.org/w/api.php?format=json&"
    s = _json(api + "action=query&list=search&srlimit=" + str(n) +
              "&srsearch=" + urllib.parse.quote(query))
    titles = [h["title"] for h in s.get("query", {}).get("search", [])]
    out: list[str] = []
    for t in titles:
        d = _json(api + "action=query&prop=extracts&explaintext=1&redirects=1&titles="
                  + urllib.parse.quote(t))
        for p in d.get("query", {}).get("pages", {}).values():
            ex = (p.get("extract") or "").strip()
            if ex:
                ex = re.sub(r"\n{2,}", "\n", ex)[:per]
                out.append(f"## Wikipedia: {t}\n{ex}")
    return out


def _ddg_ia(query: str, cap: int = 1400) -> str:
    d = _json("https://api.duckduckgo.com/?format=json&no_html=1&skip_disambig=1&q="
              + urllib.parse.quote(query))
    bits: list[str] = []
    if d.get("AbstractText"):
        bits.append(d["AbstractText"])
    for rt in d.get("RelatedTopics", []):
        if isinstance(rt, dict) and rt.get("Text"):
            bits.append(rt["Text"])
        if sum(len(b) for b in bits) > cap:
            break
    return ("## DuckDuckGo\n" + " | ".join(bits))[:cap] if bits else ""


def web_research(query: str, max_pages: int = 3, max_chars: int = 3500) -> str:
    parts: list[str] = []
    try:
        parts += _wiki(query, min(max(max_pages, 1), 3))
    except Exception as e:  # noqa: BLE001
        parts.append(f"(wikipedia unavailable: {e})")
    if sum(len(p) for p in parts) < 400:
        try:
            ddg = _ddg_ia(query)
            if ddg:
                parts.append(ddg)
        except Exception:
            pass
    real = [p for p in parts if not p.startswith("(wikipedia unavailable")]
    if not real:
        return f"No research results for: {query} ({'; '.join(parts) if parts else 'no sources reachable'})"
    return ("Web research for: " + query + "\n\n" + "\n\n".join(parts))[:max_chars]
