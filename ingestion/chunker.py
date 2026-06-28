"""Sliding-window text chunker with sentence-boundary alignment and configurable overlap."""

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