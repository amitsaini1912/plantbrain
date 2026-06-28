"""
pipeline.py
-----------
Ties the loader and chunker together into one simple call: ingest_file().

This is the public face of the ingestion module. The rest of the app doesn't
need to know about PDFs, Word files, or chunking rules — it just calls
ingest_file("manual.pdf") and gets back a clean list of chunk records, each
with a stable id and the metadata needed for citations.

Flow:   file on disk  ->  load_document()  ->  chunk_text() per page  ->  records
"""

import hashlib

from .loader import load_document
from .chunker import chunk_text


def _make_id(source: str, index: int) -> str:
    """
    Build a short, STABLE id for a chunk from its filename + position.

    Stable = re-ingesting the same file produces the same ids, so we never end
    up with duplicate copies of the same chunk in the database.
    """
    raw = f"{source}-{index}"
    return hashlib.md5(raw.encode()).hexdigest()[:12]


def ingest_file(path: str, chunk_size: int = 1000, overlap: int = 150) -> list[dict]:
    """
    Read a file and return a list of chunk records ready to be embedded/stored.

    Each record looks like:
        {
            "id":          "a1b2c3d4e5f6",   # stable unique id
            "text":        "Pump P-101 shall be inspected ...",
            "source":      "pump_manual.pdf",
            "page":        7,                 # or None for Word/text files
            "chunk_index": 12,                # position within the document
        }
    """
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