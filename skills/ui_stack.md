# UI Stack — Advay's Frontend Skills

All UI tools, patterns, and frameworks used across projects.

---

## Core Frameworks

| Framework | Use Case | Projects |
|---|---|---|
| **Streamlit** | Python ML/data UIs, rapid prototyping | GNN-PCNA pocket predictor |
| **React + Vite** | Production web apps | OpenMontage, landing pages |
| **Next.js** | SSR web apps | RealStandards, faceless pipeline landing |
| **Remotion** | Programmatic video in React/JS | OpenMontage |
| **Svelte** | Lightweight interactive UIs | Experimental |

## Styling

| Tool | Purpose |
|---|---|
| **Tailwind CSS** | Utility-first, rapid composition |
| **shadcn/ui** | Accessible component primitives |
| **Framer Motion** | Production animations, gestures |
| **CSS custom properties** | Design tokens, theme switching |
| **magic-mcp** | Logo search (`api.svgl.app`), shadcn pattern gen in Claude |

## 3D & Animation

| Tool | Purpose |
|---|---|
| **Spline** | Interactive 3D scenes in browser (no Three.js code needed) |
| **Three.js** | Custom 3D, WebGL |
| **ManimGL** | Math/ML animations (3Blue1Brown style) — 80+ examples in OpenMontage |
| **ManimCE** | Math animation community edition — `manim render scene.py SceneName` |
| **D3.js** | Data-driven SVG visualizations |
| **Plotly** | Interactive charts in Streamlit/React |
| **matplotlib** | Static scientific plots (Agg backend for Streamlit) |

## Component Patterns Used

### Glassmorphism
```css
background: rgba(255, 255, 255, 0.05);
backdrop-filter: blur(12px);
border: 1px solid rgba(255, 255, 255, 0.1);
border-radius: 16px;
```

### Bento Grid
```jsx
<div className="grid grid-cols-3 grid-rows-2 gap-4">
  <div className="col-span-2 row-span-2">large card</div>
  <div>small card</div>
  <div>small card</div>
</div>
```

### Dark mode base
```jsx
<div className="min-h-screen bg-zinc-950 text-zinc-50">
```

### Luxury card
```jsx
<div className="
  bg-gradient-to-br from-zinc-900 to-zinc-950
  border border-zinc-800 rounded-2xl p-6
  shadow-[0_0_60px_rgba(0,0,0,0.5)]
  hover:border-zinc-600 transition-all duration-300
">
```

### Sequence heatmap (Streamlit + matplotlib)
```python
fig, ax = plt.subplots(figsize=(18, 2.4))
ax.imshow(scores[np.newaxis, :], aspect="auto", cmap="RdYlGn_r", vmin=0, vmax=1)
```

### DBSCAN pocket clustering
```python
from sklearn.cluster import DBSCAN
db = DBSCAN(eps=6.0, min_samples=3, metric="euclidean").fit(coords)
```

## Design Vocabulary

- **Color base**: zinc-950 (almost black), zinc-900, zinc-800
- **Accent**: blue-500 / violet-500 / emerald-400 depending on domain
- **Typography**: Inter (UI), Geist Mono (code), Playfair Display (luxury headings)
- **Motion**: `ease-out` curves, 200-300ms transitions, spring physics for modals
- **Spacing**: 4px grid (Tailwind default)
- **Shadows**: large ambient `shadow-2xl` + tight inner shadows

## MCP Tools for UI

- `magic-mcp` — logo search + shadcn component lookup, internalized in Claude sessions
- `mcp__claude_ai_Canva__*` — Canva design tools via MCP
- `ui-ux-pro-max` skill — 67 styles, 96 palettes, 57 font pairings in Claude Code
- `frontend-design` skill — production-grade component generation

## Manim Examples (OpenMontage)

80+ ManimGL examples at `Obsidian/OpenMontage/.agents/skills/manimgl-best-practices/examples/`:
- Attention mechanism visualization
- MLP forward pass
- Neural network block flow
- Transformer token embeddings
- Gradient descent basin
- DBSCAN clustering (relevant for pocket prediction)
- Lorenz attractor, quantum gates, wave functions

Run ManimCE:
```bash
cd OpenMontage
manim render .agents/skills/manimce-best-practices/examples/basic_animations.py SceneName -pql
```

Run ManimGL:
```bash
manimgl .agents/skills/manimgl-best-practices/examples/neural_network_basic.py
```

## Video Generation Stack (OpenMontage)

```
OpenMontage/
  12 workflows: explainer, documentary, trailer, podcast, lecture, demo, ...
  52 integrated tools
  Stack: Python 3.10+ / Remotion / React / FFmpeg / Node.js 18+
  Config: config.yaml (API keys, providers)
  Skills: .agents/skills/ or .claude/skills/
```

Start video pipeline:
```bash
cd C:/Users/advay/Obsidian/OpenMontage
# Read CLAUDE.md first for usage instructions
cat CLAUDE.md
```
