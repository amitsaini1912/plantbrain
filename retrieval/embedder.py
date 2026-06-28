"""
embedder.py
-----------
Thin wrapper around a sentence-transformers model.

We load the model once and reuse it across the session. Using all-MiniLM-L6-v2:
  - 384 dimensions, fast inference, good retrieval quality for technical text
  - Runs fully locally, no API quota consumed on embedding
"""

from __future__ import annotations
import numpy as np
from config import EMBED_MODEL


class Embedder:
    _instance: "Embedder | None" = None

    def __init__(self) -> None:
        from sentence_transformers import SentenceTransformer
        self._model = SentenceTransformer(EMBED_MODEL)

    @classmethod
    def get(cls) -> "Embedder":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def embed(self, texts: list[str]) -> np.ndarray:
        """Return a (N, 384) float32 matrix of L2-normalised embeddings."""
        vecs = self._model.encode(
            texts,
            batch_size=32,
            show_progress_bar=False,
            normalize_embeddings=True,   # cosine sim becomes a dot product
            convert_to_numpy=True,
        )
        return vecs.astype(np.float32)

    def embed_one(self, text: str) -> np.ndarray:
        return self.embed([text])[0]
