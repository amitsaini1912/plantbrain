# PlantBrain

An AI assistant for industrial plants — upload maintenance logs, equipment manuals, SOPs, and incident reports, then ask questions across all of them in plain English.

Built for ET AI Hackathon 2026 · Problem Statement 8.

## What it does

**Knowledge Copilot** — ask anything about your plant documents and get a cited answer with the source document and page number.

**Knowledge Graph** — automatically maps equipment, procedures, regulations, and their relationships into an interactive graph as you upload documents.

**Maintenance & RCA** — describe a failure and get a root cause analysis grounded in your own work order history and equipment manuals, not generic training data.

**Compliance Monitor** — checks your documents against Factory Act, OISD, and PESO requirements and flags gaps with recommended corrective actions.

## Stack

Python 3.11 · Streamlit · Anthropic Claude (claude-sonnet-4-6) · sentence-transformers (all-MiniLM-L6-v2) · NumPy · NetworkX · Pyvis · PyMuPDF · python-docx

## Setup

```bash
python -m venv .venv
.venv\Scripts\activate        # Windows
pip install -r requirements.txt
```

Add your Anthropic API key to `.env`:

```
ANTHROPIC_API_KEY=sk-ant-...
```

Run:

```bash
streamlit run app.py
```

The app works without an API key — entity extraction and compliance checking fall back to regex-based logic, and the copilot returns the raw top matching passage.

## Quick demo

Click **"Load sample docs"** in the sidebar. This loads 5 pre-built documents (pump manual, confined space SOP, maintenance log, incident report, regulatory extracts) into the knowledge base. Then try:

- *"What caused the P-101 seal failures in 2023?"*
- *"What are the atmospheric limits for confined space entry?"*
- *"Which OISD clauses apply to hot work?"*

## Project structure

```
app.py              Streamlit UI (5 tabs)
config.py           Central config (model names, chunk sizes, etc.)
ingestion/          Document loading and chunking pipeline
retrieval/          Embedder + numpy vector store with disk persistence
agents/             copilot · entity_extractor · compliance · rca
graph/              Knowledge graph builder (networkx + pyvis)
sample_docs/        Demo documents for the quick-start button
make_samples.py     Script that generated the sample documents
store/              Created at runtime — vector store + graph HTML
```

## Team

Amit Saini — [github.com/amitsaini1912](https://github.com/amitsaini1912)
