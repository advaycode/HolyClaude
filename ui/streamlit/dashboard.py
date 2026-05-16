"""
dashboard.py — HolyClaude Streamlit research dashboard.

Unified UI for: vault search, crawl status, agent runs, knowledge graph stats,
scholarship tracker, and overnight reports.

Run:
    streamlit run ui/streamlit/dashboard.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import streamlit as st

REPO_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(REPO_ROOT))

# ── page config ───────────────────────────────────────────────────────────────

st.set_page_config(
    page_title="HolyClaude",
    page_icon="🧠",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown("""
<style>
    .main { background-color: #0f0f1a; }
    .stApp { background-color: #0f0f1a; }
    .block-container { padding-top: 1rem; }
    .metric-card {
        background: linear-gradient(135deg, #1e1e2e, #1a1a3e);
        border: 1px solid #374151;
        border-radius: 12px;
        padding: 1rem;
    }
    .agent-tag {
        display: inline-block;
        background: #1e3a5f;
        border: 1px solid #3b82f6;
        border-radius: 6px;
        padding: 2px 8px;
        font-size: 12px;
        color: #93c5fd;
        margin: 2px;
    }
    div[data-testid="stMetric"] {
        background: linear-gradient(135deg, #1e1e2e, #1a2a3e);
        border: 1px solid #374151;
        border-radius: 10px;
        padding: 0.75rem 1rem;
    }
</style>
""", unsafe_allow_html=True)


# ── sidebar ───────────────────────────────────────────────────────────────────

with st.sidebar:
    st.markdown("## 🧠 HolyClaude")
    st.markdown("---")

    vault_path = st.text_input(
        "Vault Directory",
        value="C:/Users/advay/Obsidian",
        help="Path to your Obsidian vault",
    )
    data_path = st.text_input(
        "Data Directory",
        value=str(REPO_ROOT / "data"),
    )

    st.markdown("---")
    page = st.radio(
        "Navigate",
        ["Overview", "Vault Search", "Crawl Catalog", "Scholarships", "Knowledge Graph", "Overnight Reports", "Agent Runner"],
    )

    st.markdown("---")
    # Ollama status
    try:
        from agents.base_agent import OllamaAgent
        agent = OllamaAgent()
        ok = agent.health_check()
        models = agent.list_models() if ok else []
        st.success(f"Ollama ✓  {len(models)} models") if ok else st.error("Ollama offline")
        if ok and models:
            selected_model = st.selectbox("Model", models, index=0)
        else:
            selected_model = "gemma3:4b"
    except Exception:
        st.error("Agents not importable")
        selected_model = "gemma3:4b"


# ── overview ──────────────────────────────────────────────────────────────────

if page == "Overview":
    st.title("HolyClaude Dashboard")

    col1, col2, col3, col4 = st.columns(4)

    vault = Path(vault_path)
    n_notes = len(list(vault.rglob("*.md"))) if vault.exists() else 0
    with col1:
        st.metric("Vault Notes", f"{n_notes:,}")

    data_dir = Path(data_path)
    catalogs = list(data_dir.rglob("catalog.json")) if data_dir.exists() else []
    with col2:
        st.metric("Catalogs", len(catalogs))

    scholar_files = list(data_dir.rglob("*scholarships.json")) if data_dir.exists() else []
    scholar_count = 0
    for f in scholar_files:
        try:
            scholar_count += len(json.loads(f.read_text()))
        except Exception:
            pass
    with col3:
        st.metric("Scholarships Tracked", scholar_count)

    overnight_files = list(data_dir.rglob("*overnight_report.json")) if data_dir.exists() else []
    with col4:
        st.metric("Overnight Reports", len(overnight_files))

    st.markdown("---")

    # Agent catalog
    st.subheader("Agent Catalog")
    agents_info = [
        ("OllamaAgent",      "base_agent.py",        "Base class — streaming, health, multi-turn",         "#1e3a5f"),
        ("CrawlerAgent",     "crawler_agent.py",      "PubMed · ArXiv · GitHub · Zenodo · L1–L5 validate",  "#1e3a5f"),
        ("VerifierAgent",    "verifier_agent.py",     "Gemma L6 LLM-as-judge, 1–10 scoring",                "#1e3a5f"),
        ("HubWriter",        "hub_writer.py",         "KNOWLEDGE_GRAPH.md + hub notes",                     "#164e63"),
        ("PromptOptimizer",  "prompt_optimizer.py",   "classify → route → compress → inject → decompose",   "#164e63"),
        ("CodeAgent",        "code_agent.py",         "implement · review · plan — reads CLAUDE.md",         "#164e63"),
        ("DiffAgent",        "diff_agent.py",         "git diff → per-hunk review · severity · PR summary", "#1a3a2a"),
        ("ResearchPipeline", "research_pipeline.py",  "YouTube (yt-dlp) → NotebookLM → vault",              "#1a3a2a"),
        ("StudyAgent",       "study_agent.py",        "AP Physics/Stats daily rotation, state.json",         "#1a3a2a"),
        ("OvernightAgent",   "overnight_agent.py",    "Batch scheduler · threading · morning briefing",      "#3a1a2a"),
        ("PlaywrightAgent",  "playwright_agent.py",   "Browser scraping · schema extraction · screenshots",  "#3a1a2a"),
        ("ScholarAgent",     "scholar_agent.py",      "Scholarship scraper · filter · rank · vault",         "#3a1a2a"),
        ("GraphAgent",       "graph_agent.py",        "networkx · PageRank · community detection · D3",      "#2a1a3a"),
    ]

    cols = st.columns(2)
    for i, (name, file, desc, color) in enumerate(agents_info):
        with cols[i % 2]:
            st.markdown(f"""
            <div style="background:{color};border:1px solid #374151;border-radius:8px;padding:10px;margin:4px 0">
                <strong style="color:#e2e8f0">{name}</strong>
                <span style="color:#6b7280;font-size:12px;margin-left:8px">{file}</span><br>
                <span style="color:#94a3b8;font-size:13px">{desc}</span>
            </div>
            """, unsafe_allow_html=True)


# ── vault search ──────────────────────────────────────────────────────────────

elif page == "Vault Search":
    st.title("Vault Search")

    query = st.text_input("Search query", placeholder="PCNA cryptic pocket GNN...")
    col1, col2, col3 = st.columns(3)
    with col1:
        n_results = st.slider("Max results", 3, 20, 8)
    with col2:
        note_type_filter = st.selectbox("Note type", ["any", "article", "preprint", "dataset", "note", "hub"])
    with col3:
        use_tfidf = st.checkbox("TF-IDF (fast)", value=True)

    if query:
        vault = Path(vault_path)
        if not vault.exists():
            st.error(f"Vault not found: {vault}")
        else:
            with st.spinner("Searching..."):
                if use_tfidf:
                    try:
                        from utils.vault_index import VaultIndex
                        idx = VaultIndex(vault)
                        if not idx.load():
                            st.info("Building index (first run)...")
                            idx.build()
                            idx.save()
                        ntype = note_type_filter if note_type_filter != "any" else None
                        results = idx.search(query, n=n_results, note_type=ntype)
                        st.caption(f"{len(results)} results  ·  {idx.stats()['notes_indexed']:,} notes indexed")
                        for r in results:
                            with st.expander(f"**{r.note_name}**  `{r.note_type}`  score={r.score:.4f}"):
                                st.markdown(f"**Path:** `{r.note_path}`")
                                st.markdown(f"**Tags:** {', '.join(r.tags) if r.tags else '—'}")
                                st.markdown(f"**Snippet:**\n> {r.snippet}")
                    except ImportError as e:
                        st.error(f"Import error: {e}")
                else:
                    # Fallback: simple keyword match
                    kws = query.lower().split()
                    results = []
                    for md in Path(vault_path).rglob("*.md"):
                        try:
                            text = md.read_text(encoding="utf-8", errors="ignore")
                            score = sum(1 for k in kws if k in text.lower())
                            if score:
                                results.append((score, md, text[:300]))
                        except Exception:
                            pass
                    results.sort(reverse=True)
                    for score, md, preview in results[:n_results]:
                        with st.expander(f"**{md.stem}**  score={score}"):
                            st.markdown(f"`{md}`")
                            st.text(preview)


# ── crawl catalog ─────────────────────────────────────────────────────────────

elif page == "Crawl Catalog":
    st.title("Crawl Catalog Viewer")

    data_dir = Path(data_path)
    catalogs = sorted(data_dir.rglob("catalog.json"), key=lambda f: f.stat().st_mtime, reverse=True) if data_dir.exists() else []

    if not catalogs:
        st.info("No catalogs found. Run a crawl first.")
        st.code("python cli.py crawl 'your topic' --keywords kw1 kw2 --verify")
    else:
        selected = st.selectbox("Catalog", [str(c) for c in catalogs])
        catalog_path = Path(selected)

        try:
            catalog = json.loads(catalog_path.read_text(encoding="utf-8"))
            records = catalog.get("passed", catalog.get("all_records", []))
            stats = catalog.get("stats", {})

            col1, col2, col3, col4 = st.columns(4)
            with col1: st.metric("Total Records", stats.get("total", len(records)))
            with col2: st.metric("Passed", stats.get("passed", len(records)))
            with col3: st.metric("Verified", sum(1 for r in records if r.get("gemma_score")))
            with col4: st.metric("Avg Gemma", f"{sum(r.get('gemma_score',0) for r in records if r.get('gemma_score')) / max(1, sum(1 for r in records if r.get('gemma_score'))):.1f}")

            st.markdown("---")

            # Filters
            col1, col2 = st.columns(2)
            with col1:
                min_gemma = st.slider("Min Gemma score", 1, 10, 1)
            with col2:
                record_type = st.selectbox("Record type", ["all"] + list({r.get("record_type","") for r in records}))

            filtered = [r for r in records
                        if (r.get("gemma_score", 0) or 0) >= min_gemma
                        and (record_type == "all" or r.get("record_type") == record_type)]

            st.caption(f"Showing {len(filtered)} / {len(records)} records")

            for rec in filtered[:40]:
                score = rec.get("gemma_score", "—")
                rel = rec.get("relevance", 0)
                badge = "🔴" if (score or 0) >= 8 else "🟡" if (score or 0) >= 6 else "⚪"
                with st.expander(f"{badge} **{(rec.get('title') or rec.get('uid','?'))[:80]}**  `{rec.get('source','')}`  Gemma={score}  rel={rel:.2f}"):
                    st.markdown(f"**URL:** {rec.get('url','—')}")
                    st.markdown(f"**Type:** {rec.get('record_type','—')}  |  **UID:** `{rec.get('uid','—')}`")
                    if rec.get("description"):
                        st.markdown(f"**Abstract:** {rec['description'][:400]}")
                    if rec.get("gemma_reason"):
                        st.markdown(f"**Gemma reason:** _{rec['gemma_reason']}_")
        except Exception as e:
            st.error(f"Error loading catalog: {e}")


# ── scholarships ──────────────────────────────────────────────────────────────

elif page == "Scholarships":
    st.title("Scholarship Tracker")

    data_dir = Path(data_path)
    scholar_files = sorted(data_dir.rglob("*scholarships.json"), key=lambda f: f.stat().st_mtime, reverse=True) if data_dir.exists() else []

    if not scholar_files:
        st.info("No scholarship data found. Run the scraper first.")
        st.code("python workflows/scholar_flow.py --min-amount 500 --deadline-within 90")
    else:
        selected = st.selectbox("File", [str(f) for f in scholar_files])
        try:
            scholarships = json.loads(Path(selected).read_text(encoding="utf-8"))

            urgent = [s for s in scholarships if s.get("urgency") == "urgent"]
            soon   = [s for s in scholarships if s.get("urgency") == "soon"]
            col1, col2, col3 = st.columns(3)
            with col1: st.metric("Total", len(scholarships))
            with col2: st.metric("🔴 Urgent (<14d)", len(urgent))
            with col3: st.metric("🟡 Soon (<45d)", len(soon))

            st.markdown("---")
            urgency_filter = st.multiselect("Urgency", ["urgent", "soon", "open", "unknown"], default=["urgent", "soon", "open"])
            filtered = [s for s in scholarships if s.get("urgency") in urgency_filter]

            for s in filtered[:30]:
                urgency = s.get("urgency", "unknown")
                icon = {"urgent": "🔴", "soon": "🟡", "open": "🟢", "expired": "⚫"}.get(urgency, "⚪")
                amt = f"${s.get('amount', 0):,.0f}" if s.get('amount') else "?"
                days = s.get("days_until")
                days_str = f"{days}d" if days is not None else "?"
                with st.expander(f"{icon} **{s.get('name','?')[:60]}**  {amt}  due in {days_str}  `{s.get('source','')}`"):
                    st.markdown(f"**Deadline:** {s.get('deadline_parsed') or s.get('deadline','—')}")
                    st.markdown(f"**URL:** {s.get('url','—')}")
                    if s.get('description'):
                        st.markdown(f"**Description:** {s['description'][:300]}")
                    st.markdown(f"- [ ] Check eligibility\n- [ ] Prepare materials\n- [ ] Submit by deadline")
        except Exception as e:
            st.error(f"Error: {e}")


# ── knowledge graph ───────────────────────────────────────────────────────────

elif page == "Knowledge Graph":
    st.title("Knowledge Graph Stats")

    vault = Path(vault_path)
    if not vault.exists():
        st.error(f"Vault not found: {vault}")
    else:
        if st.button("Build Graph", type="primary"):
            with st.spinner("Parsing wikilinks and computing PageRank..."):
                try:
                    from agents.graph_agent import GraphAgent
                    agent = GraphAgent(vault_dir=vault, min_connections=2)
                    graph = agent.build()
                    st.session_state["graph"] = graph
                    st.session_state["graph_agent"] = agent
                except ImportError as e:
                    st.error(f"Import error: {e}")

        if "graph" in st.session_state:
            graph = st.session_state["graph"]
            agent = st.session_state["graph_agent"]

            col1, col2, col3, col4 = st.columns(4)
            with col1: st.metric("Nodes", graph.stats["total_nodes"])
            with col2: st.metric("Edges", graph.stats["total_edges"])
            with col3: st.metric("Communities", graph.stats["n_communities"])
            with col4: st.metric("Hub Notes (≥5 links)", graph.stats["hub_notes"])

            st.markdown("---")
            col1, col2 = st.columns(2)

            with col1:
                st.subheader("Top Nodes — PageRank")
                top_pr = agent.top_nodes(graph, n=15, metric="pagerank")
                for node in top_pr:
                    st.markdown(f"`C{node.community:02d}` **{node.name}** — PR={node.pagerank:.5f}  in={node.in_degree}")

            with col2:
                st.subheader("Top Nodes — In-Degree (most linked)")
                top_id = agent.top_nodes(graph, n=15, metric="in_degree")
                for node in top_id:
                    st.markdown(f"`C{node.community:02d}` **{node.name}** — in={node.in_degree}  out={node.out_degree}")

            st.markdown("---")
            st.subheader("Communities")
            for comm_id, members in sorted(graph.communities.items(), key=lambda x: -len(x[1]))[:10]:
                with st.expander(f"Community {comm_id} — {len(members)} notes"):
                    st.markdown("  ".join(f"`{m}`" for m in sorted(members)[:40]))


# ── overnight reports ─────────────────────────────────────────────────────────

elif page == "Overnight Reports":
    st.title("Overnight Reports")

    data_dir = Path(data_path)
    reports = sorted(data_dir.rglob("*overnight_report.json"), key=lambda f: f.stat().st_mtime, reverse=True) if data_dir.exists() else []

    if not reports:
        st.info("No reports yet.")
        st.code("python cli.py overnight --research 'AlphaFold' --study ap-physics")
    else:
        for report_path in reports[:5]:
            try:
                report = json.loads(report_path.read_text(encoding="utf-8"))
                date_str = report_path.stem.replace("_overnight_report", "")
                done = sum(1 for t in report.get("tasks", []) if t["status"] == "done")
                total = len(report.get("tasks", []))
                with st.expander(f"**{date_str}** — {done}/{total} tasks  ·  {report.get('total_elapsed', 0):.0f}s"):
                    st.markdown(f"**Briefing:**\n\n{report.get('briefing', '—')}")
                    st.markdown("**Tasks:**")
                    for t in report.get("tasks", []):
                        icon = "✅" if t["status"] == "done" else "❌"
                        st.markdown(f"{icon} **{t['label']}** ({t['elapsed']:.1f}s)  {t.get('result_summary','')[:80]}")
            except Exception as e:
                st.error(f"{report_path.name}: {e}")


# ── agent runner ──────────────────────────────────────────────────────────────

elif page == "Agent Runner":
    st.title("Agent Runner")
    st.caption("Run agents directly from the dashboard")

    tab1, tab2, tab3 = st.tabs(["Ask Ollama", "Optimize Prompt", "Run Crawler"])

    with tab1:
        prompt = st.text_area("Prompt", height=120)
        system = st.text_input("System prompt (optional)")
        if st.button("Run", key="ask"):
            try:
                from agents.base_agent import OllamaAgent
                agent = OllamaAgent(model=selected_model)
                with st.spinner("Thinking..."):
                    result = agent.chat(prompt, system=system or None, stream=False, print_stream=False)
                st.markdown("**Response:**")
                st.markdown(result)
            except Exception as e:
                st.error(str(e))

    with tab2:
        prompt2 = st.text_area("Prompt to optimize", height=100)
        domain = st.text_input("Domain context", placeholder="GNN-PCNA research")
        llm_classify = st.checkbox("Use LLM classify (slower)")
        if st.button("Optimize", key="opt"):
            try:
                from agents.prompt_optimizer import PromptOptimizer
                opt = PromptOptimizer(domain_context=domain, run_local=False)
                plan = opt.optimize(prompt2, use_llm_classify=llm_classify)
                st.markdown(f"**Task type:** `{plan.task_type}`")
                st.markdown(f"**Model:** `{plan.routing['model']}`  **Temp:** `{plan.routing['temperature']}`")
                st.markdown(f"**Strategy:** {plan.routing['strategy']}")
                if plan.vault_snippets:
                    with st.expander(f"Vault context ({len(plan.vault_snippets)} snippets)"):
                        for s in plan.vault_snippets:
                            st.text(s[:200])
                st.markdown("**Optimized system prompt:**")
                st.code(plan.steps[0].system if plan.steps else "")
            except Exception as e:
                st.error(str(e))

    with tab3:
        topic = st.text_input("Topic")
        keywords_raw = st.text_input("Keywords (comma-separated)")
        output = st.text_input("Output dir", value=str(Path(data_path) / "crawl"))
        col1, col2 = st.columns(2)
        with col1: workers = st.slider("Workers", 2, 8, 4)
        with col2: min_rel = st.slider("Min relevance", 0.0, 0.5, 0.1)
        if st.button("Start Crawl", key="crawl"):
            if not topic:
                st.error("Enter a topic")
            else:
                try:
                    from agents.crawler_agent import CrawlerAgent, PubMedSource, ArXivSource
                    kws = [k.strip() for k in keywords_raw.split(",") if k.strip()] or topic.split()
                    crawler = CrawlerAgent(topic=topic, keywords=kws, output_dir=Path(output), workers=workers, min_relevance=min_rel)
                    crawler.add_source(PubMedSource(queries=[f"{topic} {kws[0]}"]))
                    crawler.add_source(ArXivSource(query=topic))
                    with st.spinner("Crawling... (this may take a few minutes)"):
                        catalog = crawler.run()
                    stats = catalog.get("stats", {})
                    st.success(f"Done: {stats.get('passed', 0)} records passed")
                    st.json(stats)
                except Exception as e:
                    st.error(str(e))
