"""Numpy-backed vector store with disk persistence. Fast enough for prototype scale."""

from __future__ import annotations
import json
from pathlib import Path
import numpy as np
from config import STORE_DIR, EMBED_DIM, TOP_K


_MATRIX_PATH  = STORE_DIR / "vectors.npy"
_META_PATH    = STORE_DIR / "meta.json"


class VectorStore:
    def __init__(self) -> None:
        self._vecs: np.ndarray = np.empty((0, EMBED_DIM), dtype=np.float32)
        self._meta: list[dict] = []
        self._load_from_disk()

    # ------------------------------------------------------------------ write

    def add(self, chunks: list[dict], embeddings: np.ndarray) -> None:
        """
        Add chunk records + their embeddings.

        chunks:     list of dicts with keys id, text, source, page, chunk_index
        embeddings: (N, 384) float32 array, already L2-normalised
        """
        if len(chunks) != len(embeddings):
            raise ValueError("chunks and embeddings must have the same length")

        existing_ids = {m["id"] for m in self._meta}
        new_idx = [i for i, c in enumerate(chunks) if c["id"] not in existing_ids]
        if not new_idx:
            return

        new_vecs = embeddings[new_idx]
        new_meta = [chunks[i] for i in new_idx]

        self._vecs = np.vstack([self._vecs, new_vecs]) if len(self._vecs) else new_vecs
        self._meta.extend(new_meta)
        self._save_to_disk()

    def clear(self) -> None:
        self._vecs = np.empty((0, EMBED_DIM), dtype=np.float32)
        self._meta = []
        self._save_to_disk()

    # ------------------------------------------------------------------ read

    def search(self, query_vec: np.ndarray, top_k: int = TOP_K) -> list[dict]:
        """
        Return the top_k most similar chunks (cosine similarity via dot product).
        Each result = {**chunk_meta, "score": float}.
        """
        if len(self._meta) == 0:
            return []

        scores = self._vecs @ query_vec          # (N,)
        n = min(top_k, len(scores))
        top_idx = np.argpartition(scores, -n)[-n:]
        top_idx = top_idx[np.argsort(scores[top_idx])[::-1]]

        return [
            {**self._meta[i], "score": float(scores[i])}
            for i in top_idx
        ]

    def count(self) -> int:
        return len(self._meta)

    def all_meta(self) -> list[dict]:
        return list(self._meta)

    # ---------------------------------------------------------------- persist

    def _save_to_disk(self) -> None:
        np.save(_MATRIX_PATH, self._vecs)
        _META_PATH.write_text(json.dumps(self._meta, ensure_ascii=False), encoding="utf-8")

    def _load_from_disk(self) -> None:
        if _MATRIX_PATH.exists() and _META_PATH.exists():
            try:
                self._vecs = np.load(_MATRIX_PATH)
                self._meta = json.loads(_META_PATH.read_text(encoding="utf-8"))
            except Exception:
                pass   # corrupt state — start fresh
