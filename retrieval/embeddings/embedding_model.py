"""
Embedding Generation (HuggingFace).

Turns text into vectors using a pretrained sentence-transformers model from
HuggingFace. Wrapped behind a small abstract interface (`EmbeddingModel`) so
the vector store and retrieval pipeline never depend on sentence-transformers
directly — if we later swap in an OpenAI embedding model, we only add a new
class here, nothing else in the pipeline changes.

The model is loaded lazily (on first use, not on import) and cached as a
module-level singleton, because loading model weights is relatively slow
(hundreds of ms to a few seconds) and we don't want to repeat that on every
request.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import List

import numpy as np
from loguru import logger

from app.core.config import get_settings


class EmbeddingModel(ABC):
    """Abstract interface every embedding backend implements."""

    @abstractmethod
    def embed(self, texts: List[str]) -> np.ndarray:
        """Return an (N, dim) float32 array of embeddings for N input texts."""
        raise NotImplementedError

    @property
    @abstractmethod
    def dimension(self) -> int:
        """Size of each embedding vector — needed to size the FAISS index."""
        raise NotImplementedError


class HuggingFaceEmbedder(EmbeddingModel):
    """
    Wraps a sentence-transformers model.

    Default model (from settings.EMBEDDING_MODEL_NAME) is
    'sentence-transformers/all-MiniLM-L6-v2': a small, fast, 384-dimension
    model that's a strong default for prototyping — good semantic quality
    without needing a GPU.
    """

    def __init__(self, model_name: str | None = None):
        settings = get_settings()
        self.model_name = model_name or settings.EMBEDDING_MODEL_NAME
        self._model = None  # loaded lazily in `_ensure_loaded`
        self._dimension: int | None = None

    def _ensure_loaded(self) -> None:
        if self._model is not None:
            return
        # Imported here, not at module level, so importing this file doesn't
        # force-load the (heavy) sentence-transformers/torch stack unless an
        # embedder is actually instantiated and used.
        from sentence_transformers import SentenceTransformer

        logger.info(f"Loading embedding model '{self.model_name}' (first use, may take a moment)...")
        self._model = SentenceTransformer(self.model_name)
        self._dimension = self._model.get_sentence_embedding_dimension()
        logger.info(f"Embedding model loaded — dimension={self._dimension}")

    def embed(self, texts: List[str]) -> np.ndarray:
        self._ensure_loaded()
        if not texts:
            return np.empty((0, self.dimension), dtype="float32")
        embeddings = self._model.encode(
            texts,
            convert_to_numpy=True,
            show_progress_bar=False,
            normalize_embeddings=True,  # pre-normalize so FAISS inner product == cosine similarity
        )
        return embeddings.astype("float32")

    @property
    def dimension(self) -> int:
        self._ensure_loaded()
        return self._dimension  # type: ignore[return-value]


_embedder_singleton: HuggingFaceEmbedder | None = None


def get_embedder() -> HuggingFaceEmbedder:
    """Module-level singleton accessor — avoids reloading the model repeatedly."""
    global _embedder_singleton
    if _embedder_singleton is None:
        _embedder_singleton = HuggingFaceEmbedder()
    return _embedder_singleton
