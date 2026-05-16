/**
 * VaultSearchBar.tsx — Obsidian vault search input with result dropdown.
 *
 * Calls the HolyClaude MCP search_knowledge tool (or direct API endpoint)
 * and shows inline results with relevance scores.
 *
 * Usage:
 *   <VaultSearchBar
 *     onSelect={(result) => console.log(result.noteName)}
 *     apiBase="http://localhost:8000"
 *   />
 */

import { useEffect, useRef, useState } from "react";

// ── types ─────────────────────────────────────────────────────────────────────

interface SearchResult {
  noteName: string;
  notePath: string;
  score: number;
  snippet: string;
  noteType: string;
  tags: string[];
}

interface VaultSearchBarProps {
  onSelect?: (result: SearchResult) => void;
  placeholder?: string;
  apiBase?: string;
  debounceMs?: number;
  maxResults?: number;
}

// ── hooks ─────────────────────────────────────────────────────────────────────

function useDebounce<T>(value: T, ms: number): T {
  const [debounced, setDebounced] = useState(value);
  useEffect(() => {
    const t = setTimeout(() => setDebounced(value), ms);
    return () => clearTimeout(t);
  }, [value, ms]);
  return debounced;
}

const TYPE_COLORS: Record<string, string> = {
  article:  "text-blue-400 bg-blue-900/30 border-blue-800/50",
  preprint: "text-orange-400 bg-orange-900/30 border-orange-800/50",
  dataset:  "text-green-400 bg-green-900/30 border-green-800/50",
  hub:      "text-purple-400 bg-purple-900/30 border-purple-800/50",
  note:     "text-slate-400 bg-slate-800/50 border-slate-700/50",
};

// ── component ─────────────────────────────────────────────────────────────────

export function VaultSearchBar({
  onSelect,
  placeholder = "Search vault... (PCNA, GNN, AP Physics...)",
  apiBase = "http://localhost:8000",
  debounceMs = 300,
  maxResults = 6,
}: VaultSearchBarProps) {
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<SearchResult[]>([]);
  const [loading, setLoading] = useState(false);
  const [open, setOpen] = useState(false);
  const [selected, setSelected] = useState(-1);
  const inputRef = useRef<HTMLInputElement>(null);
  const listRef  = useRef<HTMLDivElement>(null);

  const debouncedQuery = useDebounce(query, debounceMs);

  useEffect(() => {
    if (!debouncedQuery.trim()) {
      setResults([]);
      setOpen(false);
      return;
    }
    let cancelled = false;
    setLoading(true);
    fetch(`${apiBase}/search?q=${encodeURIComponent(debouncedQuery)}&n=${maxResults}`)
      .then(r => r.json())
      .then(data => {
        if (cancelled) return;
        setResults(data.results ?? []);
        setOpen(true);
        setSelected(-1);
      })
      .catch(() => { if (!cancelled) setResults([]); })
      .finally(() => { if (!cancelled) setLoading(false); });
    return () => { cancelled = true; };
  }, [debouncedQuery, apiBase, maxResults]);

  // Keyboard navigation
  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (!open || results.length === 0) return;
    if (e.key === "ArrowDown") {
      e.preventDefault();
      setSelected(s => Math.min(s + 1, results.length - 1));
    } else if (e.key === "ArrowUp") {
      e.preventDefault();
      setSelected(s => Math.max(s - 1, -1));
    } else if (e.key === "Enter" && selected >= 0) {
      e.preventDefault();
      pick(results[selected]);
    } else if (e.key === "Escape") {
      setOpen(false);
    }
  };

  const pick = (r: SearchResult) => {
    setQuery(r.noteName);
    setOpen(false);
    onSelect?.(r);
  };

  return (
    <div className="relative w-full">
      {/* Input */}
      <div className="relative">
        <svg
          className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-500"
          fill="none" stroke="currentColor" strokeWidth={2} viewBox="0 0 24 24"
        >
          <circle cx="11" cy="11" r="8" /><path d="m21 21-4.35-4.35" />
        </svg>
        <input
          ref={inputRef}
          value={query}
          onChange={e => setQuery(e.target.value)}
          onKeyDown={handleKeyDown}
          onFocus={() => results.length > 0 && setOpen(true)}
          onBlur={() => setTimeout(() => setOpen(false), 150)}
          placeholder={placeholder}
          className="
            w-full pl-10 pr-10 py-3 rounded-xl
            bg-slate-900 border border-slate-700
            text-slate-100 placeholder-slate-500
            focus:outline-none focus:border-blue-500 focus:ring-1 focus:ring-blue-500/30
            text-sm transition-colors
          "
        />
        {loading && (
          <svg className="absolute right-3 top-1/2 -translate-y-1/2 w-4 h-4 text-blue-400 animate-spin" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2}>
            <path d="M12 2v4M12 18v4M4.93 4.93l2.83 2.83M16.24 16.24l2.83 2.83M2 12h4M18 12h4" />
          </svg>
        )}
      </div>

      {/* Dropdown */}
      {open && results.length > 0 && (
        <div
          ref={listRef}
          className="
            absolute z-50 w-full mt-2
            bg-slate-900 border border-slate-700
            rounded-xl shadow-2xl shadow-black/50
            overflow-hidden
          "
        >
          {results.map((r, i) => {
            const typeClass = TYPE_COLORS[r.noteType] ?? TYPE_COLORS.note;
            return (
              <button
                key={r.notePath}
                onMouseDown={() => pick(r)}
                onMouseEnter={() => setSelected(i)}
                className={`
                  w-full text-left px-4 py-3
                  transition-colors duration-100
                  border-b border-slate-800 last:border-0
                  ${i === selected ? "bg-blue-900/30" : "hover:bg-slate-800/50"}
                `}
              >
                <div className="flex items-center justify-between mb-1">
                  <span className="text-slate-100 font-medium text-sm font-mono">{r.noteName}</span>
                  <div className="flex items-center gap-2">
                    <span className={`text-xs px-2 py-0.5 rounded border ${typeClass}`}>
                      {r.noteType}
                    </span>
                    <span className="text-xs text-slate-500">{r.score.toFixed(3)}</span>
                  </div>
                </div>
                <p className="text-slate-400 text-xs leading-relaxed line-clamp-2">{r.snippet}</p>
                {r.tags.length > 0 && (
                  <div className="flex gap-1 mt-1">
                    {r.tags.slice(0, 3).map(t => (
                      <span key={t} className="text-xs text-slate-500">#{t}</span>
                    ))}
                  </div>
                )}
              </button>
            );
          })}
        </div>
      )}
    </div>
  );
}
