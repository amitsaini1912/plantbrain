"""TF-IDF embedder using sklearn — no model download, loads instantly."""

from __future__ import annotations
import numpy as np
from sklearn.feature_extraction.text import HashingVectorizer
from config import EMBED_DIM


class Embedder:
    _instance: "Embedder | None" = None

    def __init__(self) -> None:
        self._vec = HashingVectorizer(
            n_features=EMBED_DIM,
            norm="l2",
            alternate_sign=False,
            ngram_range=(1, 2),
        )

    @classmethod
    def get(cls) -> "Embedder":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def embed(self, texts: list[str]) -> np.ndarray:
        sparse = self._vec.transform(texts)
        return np.asarray(sparse.todense(), dtype=np.float32)

    def embed_one(self, text: str) -> np.ndarray:
        return self.embed([text])[0]
