/**
 * Root.tsx — Remotion composition registry for HolyClaude video generation.
 *
 * Register compositions here. Each composition becomes a renderable video.
 *
 * Render:
 *   npx remotion render src/Root.tsx ResearchVideo out/research.mp4 \
 *     --props='{"topic":"PCNA Cryptic Pockets","findings":["GNN achieves 0.89 AUC","13 novel pockets identified"]}'
 */

import { Composition } from "remotion";
import { ResearchVideo, ResearchVideoProps } from "./compositions/ResearchVideo";
import { OvernightBriefing, OvernightBriefingProps } from "./compositions/OvernightBriefing";

const FPS = 30;
const WIDTH = 1920;
const HEIGHT = 1080;

// Default props for preview
const RESEARCH_DEFAULTS: ResearchVideoProps = {
  topic: "PCNA Cryptic Pocket Prediction",
  subtitle: "Graph Neural Networks on protein structure",
  date: new Date().toISOString().slice(0, 10),
  accentColor: "#3b82f6",
  findings: [
    "GATv2Conv dual-branch model achieves 0.89 AUC on PCNA test set",
    "13 novel cryptic pockets identified across PCNA homotrimer",
    "Spatial + sequential edge encoding outperforms single-branch by 8%",
    "AlphaFold2 structures generalize better than experimental PDB for training",
  ],
  sources: [
    { title: "Cryptic binding sites in PCNA revealed by molecular dynamics", source: "PubMed", relevance: 0.92, gemmaScore: 9 },
    { title: "PocketMiner: predicting cryptic binding sites using GNNs", source: "ArXiv", relevance: 0.88, gemmaScore: 9 },
    { title: "Graph attention networks for protein pocket detection", source: "ArXiv", relevance: 0.81, gemmaScore: 8 },
    { title: "PCNA homotrimer structure dataset — CryptoSite benchmark", source: "Zenodo", relevance: 0.76, gemmaScore: 7 },
  ],
};

const OVERNIGHT_DEFAULTS: OvernightBriefingProps = {
  date: new Date().toISOString().slice(0, 10),
  accentColor: "#d97706",
  totalElapsed: 847,
  briefing: `- 47 papers crawled across PubMed and ArXiv on PCNA cryptic pockets
- 31 papers passed Gemma L6 verification (score ≥ 6)
- 6 YouTube videos found and sent to NotebookLM for AP Physics
- AP Physics topic: Simple Harmonic Motion — video artifact generated
- 3 Obsidian hub notes created in KNOWLEDGE_GRAPH`,
  tasks: [
    { label: "Research: PCNA cryptic pocket GNN", status: "done", elapsed: 312, result_summary: "47 papers, 31 verified" },
    { label: "Study: AP Physics 1", status: "done", elapsed: 198, result_summary: "Simple Harmonic Motion video" },
    { label: "Crawl: PCNA dataset Zenodo", status: "done", elapsed: 87, result_summary: "12 datasets found" },
    { label: "Prompt: Summarize findings", status: "done", elapsed: 23, result_summary: "Briefing generated" },
    { label: "Script: update_graph_index.py", status: "failed", elapsed: 4, error: "ModuleNotFoundError: networkx" },
  ],
};

export const RemotionRoot: React.FC = () => {
  const researchFrames =
    90 +                                              // title
    Math.max(RESEARCH_DEFAULTS.findings!.length * 40, 80) + // findings
    (RESEARCH_DEFAULTS.sources!.length > 0 ? 120 : 0) +     // sources
    60;                                               // outro

  const overnightFrames =
    Math.max(90, 50 + OVERNIGHT_DEFAULTS.tasks!.length * 12) +   // status
    Math.max(100, OVERNIGHT_DEFAULTS.briefing!.split("\n").filter(l => l.trim()).length * 20 + 20);

  return (
    <>
      <Composition
        id="ResearchVideo"
        component={ResearchVideo}
        durationInFrames={researchFrames}
        fps={FPS}
        width={WIDTH}
        height={HEIGHT}
        defaultProps={RESEARCH_DEFAULTS}
        calculateMetadata={async ({ props }) => {
          const findings = props.findings ?? [];
          const sources  = props.sources  ?? [];
          const frames =
            90 +
            Math.max(findings.length * 40, 80) +
            (sources.length > 0 ? 120 : 0) +
            60;
          return { durationInFrames: frames };
        }}
      />

      <Composition
        id="OvernightBriefing"
        component={OvernightBriefing}
        durationInFrames={overnightFrames}
        fps={FPS}
        width={WIDTH}
        height={HEIGHT}
        defaultProps={OVERNIGHT_DEFAULTS}
      />
    </>
  );
};
