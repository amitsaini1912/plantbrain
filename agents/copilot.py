"""RAG-powered Q&A agent. Embeds the question, retrieves top-k chunks, calls Claude."""

from __future__ import annotations
import anthropic
from config import ANTHROPIC_API_KEY, LLM_MODEL, TOP_K
from retrieval.embedder import Embedder
from retrieval.store import VectorStore

_SYSTEM = """You are PlantBrain Copilot, an expert industrial knowledge assistant.
You answer questions about plant equipment, maintenance procedures, safety protocols,
and regulatory compliance, strictly from the provided context.

Rules:
- Answer only from the CONTEXT block below. Never hallucinate.
- Cite your sources using [SourceName, p.X] inline.
- If the context is insufficient, say so clearly and suggest what document would help.
- Use precise engineering language. Be concise and actionable.
- For safety-critical matters, always flag the relevant regulation or SOP."""


def answer_question(
    question: str,
    store: VectorStore,
    top_k: int = TOP_K,
) -> tuple[str, list[dict]]:
    """
    RAG answer for `question`.

    Returns (answer_text, source_chunks).
    Falls back to a no-API message if ANTHROPIC_API_KEY is not set.
    """
    embedder = Embedder.get()
    q_vec = embedder.embed_one(question)
    chunks = store.search(q_vec, top_k=top_k)

    if not chunks:
        return "No documents have been ingested yet. Upload files in the Documents tab.", []

    context_parts = []
    for c in chunks:
        page = f", p.{c['page']}" if c.get("page") else ""
        context_parts.append(f"[{c['source']}{page}]\n{c['text']}")
    context = "\n\n---\n\n".join(context_parts)

    prompt = f"CONTEXT:\n{context}\n\nQUESTION: {question}"

    if not ANTHROPIC_API_KEY:
        # Graceful degradation: return the raw top chunk with a note
        top = chunks[0]
        page = f" (p.{top['page']})" if top.get("page") else ""
        return (
            f"**[Demo mode — no API key]** Top matching passage from "
            f"`{top['source']}`{page}:\n\n> {top['text'][:600]}…",
            chunks,
        )

    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
    msg = client.messages.create(
        model=LLM_MODEL,
        max_tokens=1024,
        system=_SYSTEM,
        messages=[{"role": "user", "content": prompt}],
    )
    return msg.content[0].text, chunks
