"""PlantBrain — Streamlit frontend."""

import streamlit as st
import pandas as pd
from pathlib import Path

from config import APP_NAME, APP_TAGLINE, DATA_DIR, SAMPLE_DIR, ANTHROPIC_API_KEY
from ingestion.pipeline import ingest_file
from retrieval.embedder import Embedder
from retrieval.store import VectorStore
from agents.copilot import answer_question
from agents.entity_extractor import extract_entities
from agents.compliance import run_compliance_check
from agents.rca import run_rca
from graph.builder import KnowledgeGraph

# ---
# Page config — must be the very first Streamlit call
# ---
st.set_page_config(
    page_title=APP_NAME,
    page_icon="🏭",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ---
# Custom CSS — dark industrial theme
# ---
st.markdown("""
<style>
  .metric-card {
    background: #1e1e2e; border-radius: 10px; padding: 1rem;
    border-left: 4px solid #89b4fa; margin-bottom: 0.5rem;
  }
  .status-compliant { color: #a6e3a1; font-weight: bold; }
  .status-gap       { color: #f38ba8; font-weight: bold; }
  .status-unknown   { color: #fab387; font-weight: bold; }
  .source-badge {
    background: #313244; border-radius: 6px; padding: 2px 8px;
    font-size: 0.78em; color: #89dceb; font-family: monospace;
  }
  .chat-user   { background: #1e1e2e; border-radius:8px; padding:0.6rem 1rem; margin:4px 0; }
  .chat-bot    { background: #181825; border-radius:8px; padding:0.6rem 1rem; margin:4px 0;
                 border-left: 3px solid #89b4fa; }
</style>
""", unsafe_allow_html=True)

# ---
# Session-state initialisation
# ---
def _init_state():
    defaults = {
        "chunks": [],
        "files": {},
        "chat_history": [],
        "kg": KnowledgeGraph(),
        "store_ready": False,
        "compliance_results": [],
        "rca_result": None,
        "rca_sources": [],
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v

_init_state()

# ---
# Singleton helpers (cached so they load once per session)
# ---
@st.cache_resource(show_spinner="Initialising search engine…")
def _get_embedder():
    return Embedder.get()

@st.cache_resource(show_spinner=False)
def _get_store():
    return VectorStore()

embedder = _get_embedder()
store    = _get_store()

# Sync store count so sidebar metrics are accurate
if store.count() > 0 and not st.session_state.store_ready:
    st.session_state.store_ready = True

# ---
# Helper: ingest a file, embed, store, extract entities
# ---
def _process_file(path: str, filename: str) -> int:
    chunks = ingest_file(path)
    if not chunks:
        return 0
    vecs = embedder.embed([c["text"] for c in chunks])
    store.add(chunks, vecs)
    st.session_state.chunks.extend(chunks)

    # Entity extraction (sample from up to 8 chunks to stay fast)
    combined = " ".join(c["text"] for c in chunks[:8])
    entities = extract_entities(combined)
    st.session_state.kg.add_entities(entities, source=filename)
    st.session_state.store_ready = True
    return len(chunks)

# ---
# Sidebar
# ---
with st.sidebar:
    st.image("https://img.icons8.com/fluency/96/factory.png", width=64)
    st.title(APP_NAME)
    st.caption(APP_TAGLINE)
    st.divider()

    api_ok = bool(ANTHROPIC_API_KEY)
    st.markdown(
        f"**API:** {'🟢 Connected' if api_ok else '🟡 Demo mode (no key)'}"
    )
    st.metric("Documents", len(st.session_state.files))
    st.metric("Searchable chunks", store.count())
    st.metric("Graph nodes", st.session_state.kg.node_count())
    st.metric("Graph edges", st.session_state.kg.edge_count())
    st.divider()

    # Quick-load sample documents
    st.markdown("**Demo: Load sample docs**")
    if st.button("🚀 Load all sample documents", use_container_width=True):
        sample_files = list(SAMPLE_DIR.glob("*")) if SAMPLE_DIR.exists() else []
        if not sample_files:
            st.warning("Run `python make_samples.py` first to generate sample docs.")
        else:
            for sf in sample_files:
                if sf.name in st.session_state.files:
                    continue
                dest = DATA_DIR / sf.name
                dest.write_bytes(sf.read_bytes())
                try:
                    n = _process_file(str(dest), sf.name)
                    st.session_state.files[sf.name] = n
                except Exception as e:
                    st.warning(f"{sf.name}: {e}")
            st.rerun()

    if st.button("🗑️ Clear knowledge base", use_container_width=True):
        store.clear()
        st.session_state.chunks = []
        st.session_state.files = {}
        st.session_state.chat_history = []
        st.session_state.kg = KnowledgeGraph()
        st.session_state.store_ready = False
        st.session_state.compliance_results = []
        st.session_state.rca_result = None
        st.rerun()

    st.divider()
    st.caption("PS8 · ET AI Hackathon 2026")

# ---
# Main tabs
# ---
tab_copilot, tab_graph, tab_maint, tab_comply, tab_docs = st.tabs([
    "💬 Knowledge Copilot",
    "🕸️ Knowledge Graph",
    "🔧 Maintenance & RCA",
    "⚖️ Compliance Monitor",
    "📂 Documents",
])


# TAB 1 – KNOWLEDGE COPILOT
with tab_copilot:
    st.subheader("Expert Knowledge Copilot")
    st.caption(
        "Ask anything about your plant's equipment, procedures, or maintenance history. "
        "Every answer is grounded in your documents with source citations."
    )

    if not st.session_state.store_ready:
        st.info("Load documents first — use the **Documents** tab or the sidebar **Load sample docs** button.")
    else:
        # Suggested questions
        with st.expander("💡 Suggested questions", expanded=False):
            suggestions = [
                "What are the bearing temperature alarm and trip setpoints for P-101?",
                "What atmospheric conditions are required before confined space entry?",
                "What was the root cause of the P-101 seal failures in 2023?",
                "Which OISD clause governs simultaneous operations (SIMOPS)?",
                "What is the annual overhaul checklist for pump P-101?",
                "When was the D-204 vessel last inspected and what was the result?",
            ]
            cols = st.columns(2)
            for i, q in enumerate(suggestions):
                if cols[i % 2].button(q, key=f"sug_{i}", use_container_width=True):
                    st.session_state.chat_history.append({"role": "user", "content": q})
                    with st.spinner("Searching knowledge base…"):
                        ans, srcs = answer_question(q, store)
                    st.session_state.chat_history.append({
                        "role": "assistant",
                        "content": ans,
                        "sources": srcs,
                    })
                    st.rerun()

        # Chat history
        for msg in st.session_state.chat_history:
            if msg["role"] == "user":
                st.markdown(
                    f"<div class='chat-user'>🧑‍🏭 <b>You:</b> {msg['content']}</div>",
                    unsafe_allow_html=True,
                )
            else:
                st.markdown(
                    f"<div class='chat-bot'>🤖 <b>PlantBrain:</b><br>{msg['content']}</div>",
                    unsafe_allow_html=True,
                )
                if srcs := msg.get("sources"):
                    with st.expander(f"📎 {len(srcs)} source(s) retrieved"):
                        for c in srcs:
                            page = f" · p.{c['page']}" if c.get("page") else ""
                            score_pct = int(c["score"] * 100)
                            st.markdown(
                                f"<span class='source-badge'>{c['source']}{page}</span>"
                                f"  relevance {score_pct}%",
                                unsafe_allow_html=True,
                            )
                            st.caption(c["text"][:300] + "…")

        # Chat input
        if prompt := st.chat_input("Ask a question about your plant…"):
            st.session_state.chat_history.append({"role": "user", "content": prompt})
            with st.spinner("Thinking…"):
                ans, srcs = answer_question(prompt, store)
            st.session_state.chat_history.append({
                "role": "assistant",
                "content": ans,
                "sources": srcs,
            })
            st.rerun()

        if st.session_state.chat_history:
            if st.button("🗑️ Clear chat", key="clear_chat"):
                st.session_state.chat_history = []
                st.rerun()


# TAB 2 – KNOWLEDGE GRAPH
with tab_graph:
    st.subheader("Asset & Operations Knowledge Graph")
    st.caption(
        "Automatically extracted from your documents. Nodes = equipment, regulations, "
        "processes, and parameters. Edges = relationships."
    )

    kg = st.session_state.kg
    stats = kg.stats()

    if stats["nodes"] == 0:
        st.info("Load documents to populate the knowledge graph.")
    else:
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Total nodes", stats["nodes"])
        col2.metric("Total edges", stats["edges"])
        col3.metric("Equipment tags", stats["by_type"].get("equipment", 0))
        col4.metric("Regulations", stats["by_type"].get("regulation", 0))

        st.divider()

        # Legend
        st.markdown(
            "🔴 Equipment &nbsp; 🔵 Regulation &nbsp; 🟢 Process &nbsp; "
            "🟠 Parameter &nbsp; 🟣 Location"
        )

        # Render and embed interactive graph
        try:
            html_path = kg.render_html()
            html_content = html_path.read_text(encoding="utf-8")
            st.components.v1.html(html_content, height=640, scrolling=False)
        except Exception as e:
            st.error(f"Graph render error: {e}")

        st.divider()
        st.subheader("Entity Details")
        node_names = list(kg.g.nodes())
        if node_names:
            selected = st.selectbox("Explore a node", node_names)
            if selected:
                data = kg.g.nodes[selected]
                st.markdown(f"**Type:** {data.get('kind','?').title()}")
                st.markdown(f"**Found in:** {', '.join(sorted(data.get('sources',set())))}")
                nbrs = kg.get_neighbors(selected)
                if nbrs:
                    st.markdown("**Relationships:**")
                    df = pd.DataFrame(nbrs)
                    st.dataframe(df, use_container_width=True, hide_index=True)
                else:
                    st.caption("No relationships mapped yet.")


# TAB 3 – MAINTENANCE INTELLIGENCE & RCA
with tab_maint:
    st.subheader("Maintenance Intelligence & Root Cause Analysis")
    st.caption(
        "Describe a failure event and PlantBrain will analyse equipment history, "
        "OEM manuals, and incident records to identify the root cause and recommend CAPA."
    )

    if not st.session_state.store_ready:
        st.info("Upload maintenance logs and equipment manuals first.")
    else:
        col_left, col_right = st.columns([1.2, 1])

        with col_left:
            st.markdown("#### Failure Event Input")
            failure_presets = {
                "Custom…": "",
                "P-101 mechanical seal failed again": (
                    "The mechanical seal on Pump P-101 has failed for the third time this year. "
                    "Seal pot overflow was detected at 02:30. Suction pressure PI-2101 was reading "
                    "1.8 barg at the time of failure. Vibration VT-2101A had been trending up "
                    "over the past week reaching 8.5 mm/s."
                ),
                "High vibration on P-101": (
                    "Pump P-101 vibration alarm activated (VT-2101A = 9.2 mm/s). "
                    "Discharge pressure is normal. No seal leakage visible. "
                    "Last overhaul was 14 months ago."
                ),
                "Pressure relief valve PSV-3021 stuck open": (
                    "PSV-3021 on vessel V-302 found stuck open during routine walk. "
                    "Pressure in V-302 was at operating set-point. Some polymer-like deposits "
                    "visible on valve seat. Third occurrence in 18 months."
                ),
            }
            preset = st.selectbox("Load a preset scenario", list(failure_presets.keys()))
            failure_text = st.text_area(
                "Failure description",
                value=failure_presets[preset],
                height=150,
                placeholder="Describe the failure, symptoms, conditions at time of failure…",
            )
            run_btn = st.button("🔍 Run RCA Analysis", type="primary", use_container_width=True)

        with col_right:
            st.markdown("#### Recent Work Orders")
            wo_chunks = [c for c in st.session_state.chunks
                        if "maintenance_log" in c.get("source","").lower()]
            if wo_chunks:
                records = []
                import re
                for c in wo_chunks[:6]:
                    for m in re.finditer(r"(WO#\d+)\s*\|\s*(\d{4}-\d{2}-\d{2})\s*\|\s*(\w+-?\w*)", c["text"]):
                        records.append({
                            "WO#": m.group(1), "Date": m.group(2), "Equipment": m.group(3)
                        })
                if records:
                    st.dataframe(pd.DataFrame(records[:8]), use_container_width=True, hide_index=True)
                else:
                    st.caption("Work order data found — unable to parse into table.")
            else:
                st.caption("No maintenance log loaded.")

        if run_btn and failure_text.strip():
            with st.spinner("Analysing failure against knowledge base…"):
                result, sources = run_rca(failure_text, store)
            st.session_state.rca_result = result
            st.session_state.rca_sources = sources

        if st.session_state.rca_result:
            st.divider()
            st.markdown("#### RCA Report")
            st.markdown(st.session_state.rca_result)
            if st.session_state.rca_sources:
                with st.expander(f"📎 {len(st.session_state.rca_sources)} knowledge base sources used"):
                    for c in st.session_state.rca_sources[:5]:
                        page = f" · p.{c['page']}" if c.get("page") else ""
                        st.markdown(
                            f"<span class='source-badge'>{c['source']}{page}</span>",
                            unsafe_allow_html=True,
                        )
                        st.caption(c["text"][:250] + "…")


# TAB 4 – COMPLIANCE MONITOR
with tab_comply:
    st.subheader("Regulatory Compliance Monitor")
    st.caption(
        "Checks your documents against Factory Act, OISD, and PESO requirements. "
        "Surfaces gaps and generates corrective action recommendations."
    )

    if not st.session_state.store_ready:
        st.info("Load documents to run the compliance check.")
    else:
        run_compliance = st.button(
            "▶ Run Compliance Check", type="primary", use_container_width=False
        )

        if run_compliance:
            with st.spinner("Analysing compliance against 7 regulatory requirements…"):
                results = run_compliance_check(st.session_state.chunks)
            st.session_state.compliance_results = results

        if st.session_state.compliance_results:
            results = st.session_state.compliance_results
            n_compliant = sum(1 for r in results if r["status"] == "COMPLIANT")
            n_gap       = sum(1 for r in results if r["status"] == "GAP")
            n_unknown   = sum(1 for r in results if r["status"] == "UNKNOWN")

            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Checked", len(results))
            c2.metric("✅ Compliant", n_compliant)
            c3.metric("❌ Gap found", n_gap)
            c4.metric("❓ Unknown", n_unknown)

            st.divider()

            # Summary table
            table_data = []
            for r in results:
                status_icon = {"COMPLIANT": "✅", "GAP": "❌", "UNKNOWN": "❓"}.get(r["status"], "❓")
                table_data.append({
                    "Regulation": r["regulation"],
                    "Requirement": r["requirement"][:80] + ("…" if len(r["requirement"]) > 80 else ""),
                    "Status": f"{status_icon} {r['status']}",
                })
            st.dataframe(pd.DataFrame(table_data), use_container_width=True, hide_index=True)

            # Detail cards for gaps
            gaps = [r for r in results if r["status"] in ("GAP", "UNKNOWN")]
            if gaps:
                st.divider()
                st.markdown("#### Gaps & Recommendations")
                for r in gaps:
                    icon = "❌" if r["status"] == "GAP" else "❓"
                    with st.expander(f"{icon} {r['regulation']}"):
                        st.markdown(f"**Requirement:** {r['requirement']}")
                        st.markdown(f"**Status:** {r['status']}")
                        if r.get("recommendation"):
                            st.markdown(f"**Recommendation:** {r['recommendation']}")

            # Compliant items
            compliant = [r for r in results if r["status"] == "COMPLIANT"]
            if compliant:
                st.divider()
                st.markdown("#### Evidenced Compliance")
                for r in compliant:
                    with st.expander(f"✅ {r['regulation']}"):
                        st.markdown(f"**Requirement:** {r['requirement']}")
                        if r.get("evidence"):
                            st.markdown(f"**Evidence:** *{r['evidence']}*")


# TAB 5 – DOCUMENTS
with tab_docs:
    st.subheader("Document Management")
    st.caption(
        "Upload any plant document — manuals, SOPs, maintenance logs, inspection reports, "
        "incident investigations. PlantBrain will extract, embed, and index them automatically."
    )

    uploaded = st.file_uploader(
        "Upload documents (PDF, Word, or plain text)",
        type=["pdf", "docx", "txt"],
        accept_multiple_files=True,
    )

    if uploaded:
        for uf in uploaded:
            if uf.name in st.session_state.files:
                st.info(f"`{uf.name}` already loaded.")
                continue
            dest = DATA_DIR / uf.name
            dest.write_bytes(uf.getbuffer())
            with st.spinner(f"Processing `{uf.name}`…"):
                try:
                    n = _process_file(str(dest), uf.name)
                    st.session_state.files[uf.name] = n
                    st.success(f"✅ **{uf.name}** — {n} chunks indexed, entities extracted")
                except ValueError as e:
                    st.error(f"{uf.name}: {e}")

    st.divider()
    st.markdown("#### Indexed Documents")

    if not st.session_state.files:
        st.info(
            "No documents loaded. Upload files above or use **Load sample docs** "
            "in the sidebar to get started with the demo."
        )
    else:
        doc_rows = []
        for name, n in st.session_state.files.items():
            ext = Path(name).suffix.upper().lstrip(".")
            doc_rows.append({"Document": name, "Type": ext, "Chunks": n})
        st.dataframe(pd.DataFrame(doc_rows), use_container_width=True, hide_index=True)

        with st.expander("🔍 Inspect raw chunks"):
            sample_chunks = st.session_state.chunks[:10]
            for c in sample_chunks:
                page = f"p.{c['page']}" if c.get("page") else "no page"
                st.markdown(
                    f"<span class='source-badge'>{c['source']}</span> · {page} · chunk #{c['chunk_index']}",
                    unsafe_allow_html=True,
                )
                st.caption(c["text"][:350] + "…")
                st.divider()
