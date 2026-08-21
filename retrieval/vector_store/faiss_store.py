"""
FAISS Vector Database.

Owns the actual similarity-search index. We use `IndexFlatIP` (inner
product) wrapped in `IndexIDMap2`, which lets us assign our own integer IDs
to vectors instead of relying on FAISS's implicit insertion-order IDs — that
matters because the metadata store (metadata_store.py) needs a stable ID to
map a search result back to its chunk text and source.

Since embeddings are pre-normalized (see embedding_model.py,
`normalize_embeddings=True`), inner product between two vectors is
mathematically equivalent to cosine similarity — so IndexFlatIP gives us
cosine similarity search without any extra normalization step at query time.
"""

from __future__ import annotations

from pathlib import Path
from typing import List, Tuple

import numpy as np
from loguru import logger


class FAISSVectorStore:
    def __init__(self, dimension: int):
        # Imported here so importing this module doesn't require faiss to be
        # installed unless a store is actually created.
        import faiss

        self._faiss = faiss
        self.dimension = dimension
        base_index = faiss.IndexFlatIP(dimension)
        self.index = faiss.IndexIDMap2(base_index)

    def add(self, vectors: np.ndarray, ids: List[int]) -> None:
        """Add a batch of vectors, each tagged with an explicit integer ID."""
        if vectors.shape[0] != len(ids):
            raise ValueError("Number of vectors must match number of ids.")
        if vectors.shape[1] != self.dimension:
            raise ValueError(
                f"Vector dimension {vectors.shape[1]} does not match index dimension {self.dimension}."
            )
        id_array = np.array(ids, dtype="int64")
        self.index.add_with_ids(vectors.astype("float32"), id_array)
        logger.info(f"Added {len(ids)} vector(s) to FAISS index (total now: {self.index.ntotal}).")

    def search(self, query_vector: np.ndarray, k: int = 5) -> Tuple[List[int], List[float]]:
        """
        Search for the k nearest vectors to a single query vector.

        Returns (ids, scores) — ids are the same integer IDs passed into
        `add()`, and scores are cosine similarities in [-1, 1] (in practice
        close to [0, 1] for normalized text embeddings).
        """
        if self.index.ntotal == 0:
            return [], []

        query = query_vector.reshape(1, -1).astype("float32")
        k = min(k, self.index.ntotal)  # can't return more results than exist
        scores, ids = self.index.search(query, k)

        # FAISS pads with -1 if fewer than k results exist; filter those out.
        result_ids = [int(i) for i in ids[0] if i != -1]
        result_scores = [float(s) for i, s in zip(ids[0], scores[0]) if i != -1]
        return result_ids, result_scores

    def save(self, path: str | Path) -> None:
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        self._faiss.write_index(self.index, str(path))
        logger.info(f"FAISS index saved to {path} ({self.index.ntotal} vectors).")

    @classmethod
    def load(cls, path: str | Path, dimension: int) -> "FAISSVectorStore":
        import faiss

        store = cls.__new__(cls)  # bypass __init__ to avoid creating a fresh empty index
        store._faiss = faiss
        store.dimension = dimension
        store.index = faiss.read_index(str(path))
        logger.info(f"FAISS index loaded from {path} ({store.index.ntotal} vectors).")
        return store

    @property
    def count(self) -> int:
        return self.index.ntotal
