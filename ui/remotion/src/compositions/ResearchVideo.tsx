/**
 * ResearchVideo.tsx — Remotion composition for auto-generated research briefing videos.
 *
 * Animates a research report into a clean dark-mode video:
 * - Title card with topic
 * - Key findings (animated bullet list)
 * - Source cards (paper titles + relevance scores)
 * - Call to action
 *
 * Usage:
 *   remotion render src/compositions/ResearchVideo.tsx ResearchVideo --props='{"topic":"PCNA","findings":["..."]}'
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

export interface SourceCard {
  title: string;
  source: string;  // "PubMed" | "ArXiv" | etc.
  relevance: number;
  gemmaScore?: number;
}

export interface ResearchVideoProps {
  topic: string;
  subtitle?: string;
  findings: string[];
  sources?: SourceCard[];
  accentColor?: string;
  date?: string;
}

// ── constants ─────────────────────────────────────────────────────────────────

const DARK_BG = "#0f0f1a";
const CARD_BG = "#1a1a2e";
const BORDER = "#374151";
const DEFAULT_ACCENT = "#3b82f6";

const TITLE_DURATION = 90;          // frames
const FINDINGS_PER_ITEM = 40;       // frames per finding
const SOURCES_DURATION = 120;
const OUTRO_DURATION = 60;

// ── animation helpers ─────────────────────────────────────────────────────────

function useFadeIn(startFrame: number, duration = 20) {
  const frame = useCurrentFrame();
  return interpolate(frame - startFrame, [0, duration], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
    easing: Easing.out(Easing.ease),
  });
}

function useSlideUp(startFrame: number, duration = 25) {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  return spring({
    frame: frame - startFrame,
    fps,
    config: { damping: 18, stiffness: 120, mass: 0.8 },
    durationInFrames: duration,
  });
}

// ── components ────────────────────────────────────────────────────────────────

function GlowText({ children, size = 48, color = "#e2e8f0", glow = DEFAULT_ACCENT }: {
  children: React.ReactNode;
  size?: number;
  color?: string;
  glow?: string;
}) {
  return (
    <div style={{
      fontSize: size,
      fontWeight: 700,
      color,
      textShadow: `0 0 40px ${glow}60, 0 0 80px ${glow}30`,
      lineHeight: 1.2,
    }}>
      {children}
    </div>
  );
}

function Badge({ label, color }: { label: string; color: string }) {
  return (
    <span style={{
      display: "inline-block",
      background: `${color}22`,
      border: `1px solid ${color}66`,
      borderRadius: 6,
      padding: "2px 10px",
      fontSize: 13,
      color,
      fontWeight: 600,
      marginRight: 8,
    }}>
      {label}
    </span>
  );
}

function RelevanceBar({ score, max = 10 }: { score: number; max?: number }) {
  const frame = useCurrentFrame();
  const pct = interpolate(frame, [0, 20], [0, score / max], { extrapolateRight: "clamp" });
  return (
    <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
      <div style={{ flex: 1, height: 4, background: "#374151", borderRadius: 2 }}>
        <div style={{
          width: `${pct * 100}%`,
          height: "100%",
          background: `linear-gradient(90deg, ${DEFAULT_ACCENT}, #8b5cf6)`,
          borderRadius: 2,
        }} />
      </div>
      <span style={{ color: "#9ca3af", fontSize: 12, minWidth: 28 }}>{score.toFixed(1)}</span>
    </div>
  );
}

// ── title scene ───────────────────────────────────────────────────────────────

function TitleScene({ topic, subtitle, accent, date }: {
  topic: string;
  subtitle?: string;
  accent: string;
  date?: string;
}) {
  const frame = useCurrentFrame();
  const opacity = useFadeIn(0, 20);
  const slideProgress = useSlideUp(10, 30);
  const subtitleOpacity = useFadeIn(25, 20);

  const translateY = interpolate(slideProgress, [0, 1], [40, 0]);

  return (
    <AbsoluteFill style={{
      background: `radial-gradient(ellipse at 30% 40%, ${accent}18 0%, ${DARK_BG} 60%)`,
      display: "flex",
      flexDirection: "column",
      alignItems: "center",
      justifyContent: "center",
      padding: 80,
    }}>
      {/* Grid lines */}
      <div style={{
        position: "absolute", inset: 0,
        backgroundImage: `linear-gradient(${BORDER}20 1px, transparent 1px), linear-gradient(90deg, ${BORDER}20 1px, transparent 1px)`,
        backgroundSize: "60px 60px",
        opacity: 0.5,
      }} />

      <div style={{ opacity, transform: `translateY(${translateY}px)`, textAlign: "center", zIndex: 1 }}>
        <div style={{ color: accent, fontSize: 14, fontWeight: 600, letterSpacing: 4, marginBottom: 20, textTransform: "uppercase" }}>
          HOLYCLAUDE RESEARCH BRIEFING
        </div>
        <GlowText size={56} glow={accent}>{topic}</GlowText>
        {subtitle && (
          <div style={{ opacity: subtitleOpacity, color: "#94a3b8", fontSize: 22, marginTop: 20, maxWidth: 700 }}>
            {subtitle}
          </div>
        )}
        {date && (
          <div style={{ opacity: subtitleOpacity, color: "#6b7280", fontSize: 16, marginTop: 30 }}>
            {date}
          </div>
        )}
      </div>

      {/* Accent line */}
      <div style={{
        position: "absolute",
        bottom: 80,
        width: interpolate(frame, [20, 60], [0, 300], { extrapolateRight: "clamp" }),
        height: 2,
        background: `linear-gradient(90deg, transparent, ${accent}, transparent)`,
      }} />
    </AbsoluteFill>
  );
}

// ── findings scene ────────────────────────────────────────────────────────────

function FindingsScene({ findings, accent }: { findings: string[]; accent: string }) {
  const frame = useCurrentFrame();

  return (
    <AbsoluteFill style={{
      background: DARK_BG,
      padding: "60px 80px",
      display: "flex",
      flexDirection: "column",
    }}>
      <div style={{ opacity: useFadeIn(0, 15), marginBottom: 40 }}>
        <div style={{ color: accent, fontSize: 13, fontWeight: 600, letterSpacing: 3, marginBottom: 12, textTransform: "uppercase" }}>
          Key Findings
        </div>
        <div style={{ width: 60, height: 3, background: accent, borderRadius: 2 }} />
      </div>

      <div style={{ flex: 1, display: "flex", flexDirection: "column", gap: 20 }}>
        {findings.map((finding, i) => {
          const startFrame = 15 + i * 20;
          const itemOpacity = interpolate(frame - startFrame, [0, 15], [0, 1], {
            extrapolateLeft: "clamp", extrapolateRight: "clamp",
          });
          const itemX = interpolate(frame - startFrame, [0, 20], [-30, 0], {
            extrapolateLeft: "clamp", extrapolateRight: "clamp",
            easing: Easing.out(Easing.ease),
          });

          return (
            <div key={i} style={{
              opacity: itemOpacity,
              transform: `translateX(${itemX}px)`,
              display: "flex",
              gap: 20,
              alignItems: "flex-start",
              background: CARD_BG,
              border: `1px solid ${BORDER}`,
              borderLeft: `3px solid ${accent}`,
              borderRadius: 10,
              padding: "16px 24px",
            }}>
              <div style={{
                color: accent,
                fontSize: 20,
                fontWeight: 700,
                minWidth: 32,
                lineHeight: 1.6,
              }}>
                {String(i + 1).padStart(2, "0")}
              </div>
              <div style={{ color: "#e2e8f0", fontSize: 18, lineHeight: 1.6 }}>
                {finding}
              </div>
            </div>
          );
        })}
      </div>
    </AbsoluteFill>
  );
}

// ── sources scene ─────────────────────────────────────────────────────────────

function SourcesScene({ sources, accent }: { sources: SourceCard[]; accent: string }) {
  const frame = useCurrentFrame();

  const SOURCE_COLORS: Record<string, string> = {
    PubMed:  "#22c55e",
    ArXiv:   "#ef4444",
    Zenodo:  "#3b82f6",
    GitHub:  "#a855f7",
    default: "#6b7280",
  };

  return (
    <AbsoluteFill style={{ background: DARK_BG, padding: "60px 80px", display: "flex", flexDirection: "column" }}>
      <div style={{ opacity: useFadeIn(0, 15), marginBottom: 40 }}>
        <div style={{ color: accent, fontSize: 13, fontWeight: 600, letterSpacing: 3, marginBottom: 12, textTransform: "uppercase" }}>
          Sources ({sources.length})
        </div>
        <div style={{ width: 60, height: 3, background: accent, borderRadius: 2 }} />
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 16 }}>
        {sources.slice(0, 6).map((s, i) => {
          const startFrame = 10 + i * 12;
          const op = interpolate(frame - startFrame, [0, 15], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });
          const srcColor = SOURCE_COLORS[s.source] || SOURCE_COLORS.default;

          return (
            <div key={i} style={{
              opacity: op,
              background: CARD_BG,
              border: `1px solid ${BORDER}`,
              borderRadius: 10,
              padding: "16px 20px",
            }}>
              <Badge label={s.source} color={srcColor} />
              {s.gemmaScore && <Badge label={`Gemma: ${s.gemmaScore}/10`} color={accent} />}
              <div style={{ color: "#e2e8f0", fontSize: 14, marginTop: 10, lineHeight: 1.5 }}>
                {s.title.slice(0, 90)}{s.title.length > 90 ? "…" : ""}
              </div>
              <div style={{ marginTop: 10 }}>
                <RelevanceBar score={s.relevance * 10} />
              </div>
            </div>
          );
        })}
      </div>
    </AbsoluteFill>
  );
}

// ── outro ─────────────────────────────────────────────────────────────────────

function OutroScene({ accent }: { accent: string }) {
  const opacity = useFadeIn(0, 20);
  return (
    <AbsoluteFill style={{
      background: `radial-gradient(ellipse at center, ${accent}10 0%, ${DARK_BG} 70%)`,
      display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center",
    }}>
      <div style={{ opacity, textAlign: "center" }}>
        <GlowText size={36} glow={accent}>Built with HolyClaude</GlowText>
        <div style={{ color: "#6b7280", fontSize: 18, marginTop: 16 }}>
          github.com/advaycode/HolyClaude
        </div>
      </div>
    </AbsoluteFill>
  );
}

// ── main composition ──────────────────────────────────────────────────────────

export const ResearchVideo: React.FC<ResearchVideoProps> = ({
  topic,
  subtitle,
  findings = [],
  sources = [],
  accentColor = DEFAULT_ACCENT,
  date,
}) => {
  const findingsDuration = Math.max(findings.length * FINDINGS_PER_ITEM, 80);
  const sourcesDuration  = sources.length > 0 ? SOURCES_DURATION : 0;

  return (
    <AbsoluteFill>
      {/* Title */}
      <Sequence from={0} durationInFrames={TITLE_DURATION}>
        <TitleScene topic={topic} subtitle={subtitle} accent={accentColor} date={date} />
      </Sequence>

      {/* Findings */}
      <Sequence from={TITLE_DURATION} durationInFrames={findingsDuration}>
        <FindingsScene findings={findings} accent={accentColor} />
      </Sequence>

      {/* Sources */}
      {sources.length > 0 && (
        <Sequence from={TITLE_DURATION + findingsDuration} durationInFrames={sourcesDuration}>
          <SourcesScene sources={sources} accent={accentColor} />
        </Sequence>
      )}

      {/* Outro */}
      <Sequence from={TITLE_DURATION + findingsDuration + sourcesDuration} durationInFrames={OUTRO_DURATION}>
        <OutroScene accent={accentColor} />
      </Sequence>
    </AbsoluteFill>
  );
};
