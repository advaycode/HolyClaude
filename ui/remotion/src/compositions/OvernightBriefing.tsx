/**
 * OvernightBriefing.tsx — Remotion composition for morning briefing videos.
 *
 * Renders the OvernightAgent JSON report as an animated briefing:
 * - Status dashboard (tasks done/failed with timing)
 * - Briefing text animated line by line
 * - Per-task result cards
 *
 * Usage:
 *   remotion render src/compositions/OvernightBriefing.tsx OvernightBriefing \
 *     --props='{"reportPath":"data/overnight/2026-05-16_overnight_report.json"}'
 */

import {
  AbsoluteFill,
  Easing,
  interpolate,
  Sequence,
  spring,
  useCurrentFrame,
  useVideoConfig,
} from "remotion";

// ── types ─────────────────────────────────────────────────────────────────────

interface TaskSummary {
  label: string;
  status: "done" | "failed" | "pending";
  elapsed: number;
  error?: string;
  result_summary?: string;
}

export interface OvernightBriefingProps {
  date?: string;
  briefing?: string;
  tasks?: TaskSummary[];
  totalElapsed?: number;
  accentColor?: string;
}

// ── constants ─────────────────────────────────────────────────────────────────

const DARK_BG = "#0f0f1a";
const CARD_BG = "#1a1a2e";
const BORDER  = "#374151";

function useFadeIn(startFrame: number, duration = 20) {
  const frame = useCurrentFrame();
  return interpolate(frame - startFrame, [0, duration], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
    easing: Easing.out(Easing.ease),
  });
}

// ── task status bar ───────────────────────────────────────────────────────────

function TaskStatusScene({ tasks, totalElapsed, accent }: {
  tasks: TaskSummary[];
  totalElapsed: number;
  accent: string;
}) {
  const frame = useCurrentFrame();
  const done   = tasks.filter(t => t.status === "done").length;
  const failed = tasks.filter(t => t.status === "failed").length;

  return (
    <AbsoluteFill style={{ background: DARK_BG, padding: "60px 80px", display: "flex", flexDirection: "column" }}>
      {/* Header */}
      <div style={{ opacity: useFadeIn(0, 20), marginBottom: 40 }}>
        <div style={{ color: accent, fontSize: 13, fontWeight: 600, letterSpacing: 3, textTransform: "uppercase", marginBottom: 8 }}>
          Morning Briefing
        </div>
        <div style={{ display: "flex", alignItems: "baseline", gap: 20 }}>
          <div style={{ fontSize: 48, fontWeight: 700, color: "#e2e8f0" }}>Overnight Complete</div>
          <div style={{ color: "#6b7280", fontSize: 18 }}>{totalElapsed.toFixed(0)}s</div>
        </div>
        <div style={{ display: "flex", gap: 20, marginTop: 16 }}>
          <div style={{ color: "#22c55e", fontSize: 22, fontWeight: 600 }}>✓ {done} done</div>
          {failed > 0 && <div style={{ color: "#ef4444", fontSize: 22, fontWeight: 600 }}>✗ {failed} failed</div>}
        </div>
      </div>

      {/* Progress bar */}
      <div style={{ marginBottom: 40 }}>
        <div style={{ height: 6, background: BORDER, borderRadius: 3, overflow: "hidden" }}>
          <div style={{
            width: `${interpolate(frame, [10, 50], [0, done / tasks.length * 100], { extrapolateRight: "clamp" })}%`,
            height: "100%",
            background: `linear-gradient(90deg, ${accent}, #22c55e)`,
            borderRadius: 3,
            transition: "width 0.3s ease",
          }} />
        </div>
        <div style={{ color: "#6b7280", fontSize: 13, marginTop: 6 }}>{done} / {tasks.length} tasks</div>
      </div>

      {/* Task cards */}
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12 }}>
        {tasks.map((task, i) => {
          const op = interpolate(frame - (20 + i * 8), [0, 12], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });
          const isOk = task.status === "done";
          const color = isOk ? "#22c55e" : "#ef4444";
          return (
            <div key={i} style={{
              opacity: op,
              background: CARD_BG,
              border: `1px solid ${isOk ? "#22c55e33" : "#ef444433"}`,
              borderLeft: `3px solid ${color}`,
              borderRadius: 8,
              padding: "12px 16px",
            }}>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                <span style={{ color, fontWeight: 600, fontSize: 13 }}>{isOk ? "✓ DONE" : "✗ FAILED"}</span>
                <span style={{ color: "#6b7280", fontSize: 12 }}>{task.elapsed.toFixed(1)}s</span>
              </div>
              <div style={{ color: "#e2e8f0", fontSize: 14, marginTop: 6, lineHeight: 1.4 }}>
                {task.label}
              </div>
              {task.result_summary && (
                <div style={{ color: "#94a3b8", fontSize: 12, marginTop: 4 }}>
                  {task.result_summary.slice(0, 80)}
                </div>
              )}
            </div>
          );
        })}
      </div>
    </AbsoluteFill>
  );
}

// ── briefing text scene ───────────────────────────────────────────────────────

function BriefingScene({ briefing, accent }: { briefing: string; accent: string }) {
  const frame = useCurrentFrame();
  const lines = briefing.split("\n").filter(l => l.trim());

  return (
    <AbsoluteFill style={{ background: DARK_BG, padding: "60px 80px", display: "flex", flexDirection: "column" }}>
      <div style={{ opacity: useFadeIn(0, 15), marginBottom: 32 }}>
        <div style={{ color: accent, fontSize: 13, fontWeight: 600, letterSpacing: 3, textTransform: "uppercase", marginBottom: 8 }}>
          AI Briefing
        </div>
        <div style={{ width: 50, height: 3, background: accent, borderRadius: 2 }} />
      </div>

      <div style={{ display: "flex", flexDirection: "column", gap: 14 }}>
        {lines.map((line, i) => {
          const op = interpolate(frame - (10 + i * 15), [0, 12], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });
          const x  = interpolate(frame - (10 + i * 15), [0, 15], [-20, 0], { extrapolateLeft: "clamp", extrapolateRight: "clamp", easing: Easing.out(Easing.ease) });
          const isBullet = line.startsWith("-") || line.startsWith("•");

          return (
            <div key={i} style={{
              opacity: op,
              transform: `translateX(${x}px)`,
              display: "flex",
              gap: 12,
              alignItems: "flex-start",
            }}>
              {isBullet && (
                <div style={{ color: accent, fontSize: 20, lineHeight: 1.5, minWidth: 16 }}>·</div>
              )}
              <div style={{
                color: isBullet ? "#e2e8f0" : "#94a3b8",
                fontSize: isBullet ? 18 : 16,
                lineHeight: 1.6,
                fontWeight: isBullet ? 400 : 300,
              }}>
                {line.replace(/^[-•]\s*/, "")}
              </div>
            </div>
          );
        })}
      </div>
    </AbsoluteFill>
  );
}

// ── main ──────────────────────────────────────────────────────────────────────

export const OvernightBriefing: React.FC<OvernightBriefingProps> = ({
  date = new Date().toISOString().slice(0, 10),
  briefing = "",
  tasks = [],
  totalElapsed = 0,
  accentColor = "#d97706",
}) => {
  const STATUS_DURATION   = Math.max(90, 50 + tasks.length * 12);
  const BRIEFING_DURATION = Math.max(100, briefing.split("\n").filter(l => l.trim()).length * 20 + 20);

  return (
    <AbsoluteFill>
      <Sequence from={0} durationInFrames={STATUS_DURATION}>
        <TaskStatusScene tasks={tasks} totalElapsed={totalElapsed} accent={accentColor} />
      </Sequence>
      <Sequence from={STATUS_DURATION} durationInFrames={BRIEFING_DURATION}>
        <BriefingScene briefing={briefing} accent={accentColor} />
      </Sequence>
    </AbsoluteFill>
  );
};
