"""
rca.py
------
Maintenance Intelligence & Root Cause Analysis agent.

Given a failure description and the knowledge base, Claude:
  1. Identifies the most likely root cause(s) from equipment history
  2. Cross-references OEM manuals and past incidents
  3. Recommends corrective and preventive actions (CAPA)
  4. Returns a structured RCA report
"""

from __future__ import annotations
import anthropic
from config import ANTHROPIC_API_KEY, LLM_MODEL
from retrieval.embedder import Embedder
from retrieval.store import VectorStore

_RCA_SYSTEM = """You are a senior plant reliability engineer with 20 years of experience
in oil & gas and heavy industry. You specialise in failure mode analysis, root cause
investigation, and maintenance optimisation.

When performing an RCA:
- Think through potential failure modes systematically (5-Why, Ishikawa)
- Reference specific data points from the documents provided
- Distinguish between direct cause, contributing factors, and root cause
- Provide CAPA (Corrective and Preventive Actions) with owner and timeline
- Flag any safety implications
"""

_RCA_PROMPT = """Perform a Root Cause Analysis for the following failure event.

FAILURE DESCRIPTION:
{failure}

RELEVANT DOCUMENTS (with page references):
{context}

Provide:
1. Direct Cause
2. Contributing Factors (list, each < 2 sentences)
3. Root Cause
4. Corrective Actions (immediate, ≤ 7 days)
5. Preventive Actions (long-term)
6. Lessons Learned
7. Similar Past Incidents (from documents, if any)

Be specific. Reference document sources inline using [SourceName, p.X]."""


def run_rca(failure_description: str, store: VectorStore) -> tuple[str, list[dict]]:
    """
    Run an RCA for `failure_description` using the knowledge base.
    Returns (rca_report_text, source_chunks).
    """
    embedder = Embedder.get()
    q_vec = embedder.embed_one(failure_description)
    chunks = store.search(q_vec, top_k=8)

    if not chunks:
        return "No documents loaded — upload maintenance records and manuals first.", []

    context_parts = []
    for c in chunks:
        page = f", p.{c['page']}" if c.get("page") else ""
        context_parts.append(f"[{c['source']}{page}]\n{c['text'][:600]}")
    context = "\n\n---\n\n".join(context_parts)

    if not ANTHROPIC_API_KEY:
        return (
            "**[Demo mode — no API key]**\n\n"
            "RCA requires Claude API. Top relevant passage:\n\n"
            f"> {chunks[0]['text'][:500]}…",
            chunks,
        )

    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
    msg = client.messages.create(
        model=LLM_MODEL,
        max_tokens=2048,
        system=_RCA_SYSTEM,
        messages=[{
            "role": "user",
            "content": _RCA_PROMPT.format(failure=failure_description, context=context),
        }],
    )
    return msg.content[0].text, chunks
