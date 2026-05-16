/**
 * AgentCard.tsx — Reusable React component for displaying agent status.
 *
 * Used in HolyClaude web dashboards (Next.js / React + Vite).
 * Shows agent name, status, last run, and a quick-action button.
 *
 * Usage:
 *   <AgentCard
 *     name="CrawlerAgent"
 *     description="Multi-source parallel web crawler"
 *     status="ready"
 *     lastRun="2026-05-16T03:42:00Z"
 *     onRun={() => runAgent("crawl")}
 *   />
 */

import { useState } from "react";

// ── types ─────────────────────────────────────────────────────────────────────

type AgentStatus = "ready" | "running" | "done" | "failed" | "offline";

interface AgentCardProps {
  name: string;
  description: string;
  status?: AgentStatus;
  lastRun?: string;
  lastResult?: string;
  onRun?: () => void | Promise<void>;
  tags?: string[];
  className?: string;
}

// ── status config ─────────────────────────────────────────────────────────────

const STATUS_CONFIG: Record<AgentStatus, { color: string; label: string; dot: string }> = {
  ready:   { color: "text-blue-400",  label: "Ready",   dot: "bg-blue-400" },
  running: { color: "text-yellow-400",label: "Running", dot: "bg-yellow-400 animate-pulse" },
  done:    { color: "text-green-400", label: "Done",    dot: "bg-green-400" },
  failed:  { color: "text-red-400",   label: "Failed",  dot: "bg-red-400" },
  offline: { color: "text-gray-500",  label: "Offline", dot: "bg-gray-500" },
};

function formatRelative(iso: string): string {
  const diff = Date.now() - new Date(iso).getTime();
  const mins  = Math.floor(diff / 60000);
  const hours = Math.floor(mins / 60);
  if (mins < 1)   return "just now";
  if (mins < 60)  return `${mins}m ago`;
  if (hours < 24) return `${hours}h ago`;
  return `${Math.floor(hours / 24)}d ago`;
}

// ── component ─────────────────────────────────────────────────────────────────

export function AgentCard({
  name,
  description,
  status = "ready",
  lastRun,
  lastResult,
  onRun,
  tags = [],
  className = "",
}: AgentCardProps) {
  const [loading, setLoading] = useState(false);
  const cfg = STATUS_CONFIG[status];

  const handleRun = async () => {
    if (!onRun || loading || status === "running") return;
    setLoading(true);
    try { await onRun(); }
    finally { setLoading(false); }
  };

  return (
    <div className={`
      group relative
      bg-gradient-to-br from-slate-900 to-slate-800
      border border-slate-700 hover:border-slate-500
      rounded-xl p-5
      transition-all duration-200
      hover:shadow-lg hover:shadow-blue-900/20
      ${className}
    `}>
      {/* Status dot */}
      <div className="absolute top-4 right-4 flex items-center gap-2">
        <div className={`w-2 h-2 rounded-full ${cfg.dot}`} />
        <span className={`text-xs font-medium ${cfg.color}`}>{cfg.label}</span>
      </div>

      {/* Header */}
      <div className="pr-20">
        <h3 className="text-white font-semibold text-base mb-1 font-mono">{name}</h3>
        <p className="text-slate-400 text-sm leading-relaxed">{description}</p>
      </div>

      {/* Tags */}
      {tags.length > 0 && (
        <div className="flex flex-wrap gap-1 mt-3">
          {tags.map(tag => (
            <span key={tag} className="
              text-xs px-2 py-0.5 rounded-md
              bg-blue-900/40 text-blue-300
              border border-blue-800/50
            ">
              {tag}
            </span>
          ))}
        </div>
      )}

      {/* Last run */}
      {lastRun && (
        <div className="mt-3 text-xs text-slate-500">
          Last run: <span className="text-slate-400">{formatRelative(lastRun)}</span>
          {lastResult && (
            <span className="ml-2 text-slate-500">— {lastResult.slice(0, 60)}</span>
          )}
        </div>
      )}

      {/* Action */}
      {onRun && (
        <div className="mt-4 pt-3 border-t border-slate-700/50">
          <button
            onClick={handleRun}
            disabled={loading || status === "running" || status === "offline"}
            className="
              w-full py-2 px-4 rounded-lg
              text-sm font-medium
              transition-all duration-150
              disabled:opacity-40 disabled:cursor-not-allowed
              bg-blue-600 hover:bg-blue-500 active:bg-blue-700
              text-white
              flex items-center justify-center gap-2
            "
          >
            {loading || status === "running" ? (
              <>
                <svg className="w-4 h-4 animate-spin" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2}>
                  <path d="M12 2v4M12 18v4M4.93 4.93l2.83 2.83M16.24 16.24l2.83 2.83M2 12h4M18 12h4M4.93 19.07l2.83-2.83M16.24 7.76l2.83-2.83" />
                </svg>
                Running...
              </>
            ) : "Run Agent"}
          </button>
        </div>
      )}
    </div>
  );
}
