"""Combines loader + chunker; assigns stable MD5 IDs so re-ingesting the same file is a no-op."""

import hashlib

from .loader import load_document
from .chunker import chunk_text


def _make_id(source: str, index: int) -> str:
    return hashlib.md5(f"{source}-{index}".encode()).hexdigest()[:12]


def ingest_file(path: str, chunk_size: int = 1000, overlap: int = 150) -> list[dict]:
    """Read a file and return chunk records ready to be embedded and stored."""
    records = load_document(path)
    chunks: list[dict] = []
    index = 0
    for record in records:
        for piece in chunk_text(record["text"], chunk_size=chunk_size, overlap=overlap):
            chunks.append(
                {
                    "id": _make_id(record["source"], index),
                    "text": piece,
                    "source": record["source"],
                    "page": record["page"],
                    "chunk_index": index,
                }
            )
            index += 1
    return chunks