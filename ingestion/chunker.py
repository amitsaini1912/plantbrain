"""
chunker.py
----------
Splits a long piece of text into smaller, overlapping "chunks".

WHY CHUNK AT ALL?
A page of a manual can be thousands of characters. If we search and feed an
entire page to the AI, retrieval gets fuzzy and we waste the AI's context.
Instead we break text into ~1000-character pieces. When a user asks a question,
we find the few *most relevant chunks* and answer from just those.

WHY OVERLAP?
If we cut text into clean, non-overlapping blocks, a sentence that explains an
important fact might get split across the boundary and lost. By letting each
chunk repeat the last ~150 characters of the previous one, no idea falls through
the cracks between two chunks.

We also try to end each chunk at a sentence boundary (a full stop) instead of
slicing mid-word, which keeps chunks readable and improves search quality.
"""

import re


def chunk_text(text: str, chunk_size: int = 1000, overlap: int = 150) -> list[str]:
    """
    Break `text` into overlapping chunks of roughly `chunk_size` characters.

    Args:
        text:       the raw text to split.
        chunk_size: target maximum characters per chunk.
        overlap:    characters repeated from the end of one chunk at the start
                    of the next, so context is never lost at a boundary.

    Returns:
        A list of chunk strings (empty list if the text is empty).
    """
    # Collapse runs of whitespace/newlines into single spaces so chunk sizes are
    # predictable and chunks read cleanly.
    text = re.sub(r"\s+", " ", text).strip()
    if not text:
        return []

    # Safety: overlap must be smaller than the chunk, otherwise we'd never move
    # forward and the loop would run forever.
    overlap = min(overlap, chunk_size - 1)

    chunks: list[str] = []
    start = 0
    while start < len(text):
        end = start + chunk_size

        # If this isn't the last chunk, try to end on a sentence boundary so we
        # don't cut a sentence in half. We look for the last ". " in the window,
        # but only accept it if it's past the halfway point (otherwise the chunk
        # would be too short and we'd lose efficiency).
        if end < len(text):
            window = text[start:end]
            boundary = window.rfind(". ")
            if boundary > chunk_size // 2:
                end = start + boundary + 1  # keep the full stop with this chunk

        chunk = text[start:end].strip()
        if chunk:
            chunks.append(chunk)

        # Move the window forward, stepping back by `overlap` to create the
        # overlap with the next chunk.
        next_start = end - overlap
        if next_start <= start:          # guarantee we always make progress
            next_start = start + 1

        # Nudge the start to the next space so a chunk never begins mid-word.
        space = text.find(" ", next_start)
        if space != -1 and space - next_start < 40:
            next_start = space + 1

        start = next_start

    return chunks