"""
FAISS Vector Database with native document ID filtering.

Owns the similarity-search index. Uses `IndexFlatIP` (inner product) wrapped
in `IndexIDMap2` to assign explicit integer IDs to vectors.
Supports native in-engine metadata filtering via FAISS IDSelector to guarantee
document scoping at retrieval time without post-hoc filtering.
"""

from __future__ import annotations

from pathlib import Path
from typing import List, Optional, Tuple

import numpy as np
from loguru import logger


class FAISSVectorStore:
    def __init__(self, dimension: int):
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

    def search(
        self,
        query_vector: np.ndarray,
        k: int = 5,
        allowed_ids: Optional[List[int]] = None,
    ) -> Tuple[List[int], List[float]]:
        """
        Search for the k nearest vectors to a single query vector.
        If allowed_ids is provided, FAISS restricts the search exclusively to those IDs.
        """
        if self.index.ntotal == 0:
            return [], []

        if allowed_ids is not None:
            if not allowed_ids:
                return [], []
            id_array = np.array(allowed_ids, dtype="int64")
            sel = self._faiss.IDSelectorArray(id_array)
            params = self._faiss.SearchParameters(sel=sel)
        else:
            params = None

        query = query_vector.reshape(1, -1).astype("float32")
        k_search = min(k, len(allowed_ids) if allowed_ids is not None else self.index.ntotal)

        if params is not None:
            scores, ids = self.index.search(query, k_search, params=params)
        else:
            scores, ids = self.index.search(query, k_search)

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

        store = cls.__new__(cls)
        store._faiss = faiss
        store.dimension = dimension
        store.index = faiss.read_index(str(path))
        logger.info(f"FAISS index loaded from {path} ({store.index.ntotal} vectors).")
        return store

    @property
    def count(self) -> int:
        return self.index.ntotal
