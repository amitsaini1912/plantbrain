import streamlit as st
from config import APP_NAME, APP_TAGLINE

# --- Page setup (must be the first Streamlit call) ---
st.set_page_config(page_title=APP_NAME, page_icon="🏭", layout="wide")

# --- Sidebar ---
with st.sidebar:
    st.title(f"🏭 {APP_NAME}")
    st.caption(APP_TAGLINE)
    st.divider()
    st.markdown("**Status:** scaffold running ✅")
    st.markdown("Next up: document ingestion")

# --- Main area ---
st.title(APP_NAME)
st.write(APP_TAGLINE)

tab_chat, tab_graph, tab_docs = st.tabs(
    ["💬 Knowledge Copilot", "🕸️ Knowledge Graph", "📂 Documents"]
)

with tab_chat:
    st.subheader("Ask your plant's knowledge base")
    st.info("Coming next: upload documents, then ask questions and get cited answers.")
    st.chat_input("Ask a question… (not wired up yet)")

with tab_graph:
    st.subheader("Asset & operations knowledge graph")
    st.info("Coming soon: an interactive graph of equipment, procedures, and relationships.")

with tab_docs:
    st.subheader("Your document corpus")
    st.info("Coming next: upload PDFs and Word docs here to build the knowledge base.")