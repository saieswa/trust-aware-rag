"""
Retrieval Pipeline.

This is the orchestrator: it wires together the document loader, chunker,
embedder, FAISS vector store, and metadata store into two operations that
the rest of the app actually calls:

    pipeline.index_directory(path)   -> load, chunk, embed, and store everything
    pipeline.search(query, k)        -> embed the query, search FAISS, return
                                         chunk text + metadata + similarity score

Nothing here does any LLM reasoning — this is pure retrieval. The Critic,
Synthesizer, and Verifier agents (added in later steps) will sit on top of
`search()`'s output.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List

from loguru import logger

from app.core.config import get_settings
from retrieval.chunking.text_chunker import Chunk, chunk_documents
from retrieval.embeddings.embedding_model import EmbeddingModel, get_embedder
from retrieval.loaders.document_loader import load_documents_from_directory
from retrieval.vector_store.faiss_store import FAISSVectorStore
from retrieval.vector_store.metadata_store import MetadataStore


@dataclass
class RetrievedChunk:
    """One search result: chunk content plus where it came from and how
    confident the similarity match is."""

    chunk_id: str
    doc_id: str
    text: str
    score: float
    source_title: str
    source_path: str
    chunk_index: int


class RetrievalPipeline:
    def __init__(self, embedder: EmbeddingModel | None = None):
        settings = get_settings()
        self.embedder = embedder or get_embedder()
        self.index_dir = Path(settings.FAISS_INDEX_PATH)
        self.faiss_index_path = self.index_dir.with_suffix(".index")
        self.metadata_path = self.index_dir.with_suffix(".meta.json")

        self.vector_store: FAISSVectorStore | None = None
        self.metadata_store: MetadataStore = MetadataStore()

        self._try_load_existing_index()

    # ---------------------------------------------------------------- #
    # Indexing
    # ---------------------------------------------------------------- #

    def index_directory(
        self,
        directory: str | Path,
        chunk_size: int = 500,
        chunk_overlap: int = 50,
    ) -> Dict[str, Any]:
        """
        Full indexing run: load every document in `directory`, chunk it,
        embed every chunk, and store both the vectors (FAISS) and the
        metadata (MetadataStore) — then persist both to disk.

        This rebuilds the index from scratch on each call. A future step
        (once real usage patterns exist) could add incremental
        add-one-document indexing instead.
        """
        documents = load_documents_from_directory(directory)
        if not documents:
            return {"documents_indexed": 0, "chunks_indexed": 0, "message": "No documents found."}

        chunks: List[Chunk] = chunk_documents(documents, chunk_size, chunk_overlap)
        logger.info(f"Chunked {len(documents)} document(s) into {len(chunks)} chunk(s).")

        texts = [c.text for c in chunks]
        vectors = self.embedder.embed(texts)

        self.vector_store = FAISSVectorStore(dimension=self.embedder.dimension)
        self.metadata_store = MetadataStore()

        ids = []
        for chunk in chunks:
            faiss_id = self.metadata_store.next_id()
            ids.append(faiss_id)
            self.metadata_store.add(
                faiss_id,
                {
                    "chunk_id": chunk.chunk_id,
                    "doc_id": chunk.doc_id,
                    "text": chunk.text,
                    "chunk_index": chunk.chunk_index,
                    "source_title": chunk.metadata.get("source_title", ""),
                    "source_path": chunk.metadata.get("source_path", ""),
                },
            )

        self.vector_store.add(vectors, ids)
        self._persist()

        return {
            "documents_indexed": len(documents),
            "chunks_indexed": len(chunks),
            "message": "Indexing complete.",
        }

    # ---------------------------------------------------------------- #
    # Search
    # ---------------------------------------------------------------- #

    def search(self, query: str, k: int = 5) -> List[RetrievedChunk]:
        """Embed the query and return the top-k most similar chunks."""
        if self.vector_store is None or self.vector_store.count == 0:
            logger.warning("Search called before any documents were indexed.")
            return []

        query_vector = self.embedder.embed([query])[0]
        ids, scores = self.vector_store.search(query_vector, k=k)

        results: List[RetrievedChunk] = []
        for faiss_id, score in zip(ids, scores):
            meta = self.metadata_store.get(faiss_id)
            if meta is None:
                continue
            results.append(
                RetrievedChunk(
                    chunk_id=meta["chunk_id"],
                    doc_id=meta["doc_id"],
                    text=meta["text"],
                    score=score,
                    source_title=meta["source_title"],
                    source_path=meta["source_path"],
                    chunk_index=meta["chunk_index"],
                )
            )
        return results

    # ---------------------------------------------------------------- #
    # Persistence helpers
    # ---------------------------------------------------------------- #

    def _persist(self) -> None:
        if self.vector_store is not None:
            self.vector_store.save(self.faiss_index_path)
        self.metadata_store.save(self.metadata_path)

    def _try_load_existing_index(self) -> None:
        """On startup, load a previously-built index from disk if one exists,
        so the app doesn't need to re-index on every restart."""
        if self.faiss_index_path.exists() and self.metadata_path.exists():
            try:
                self.vector_store = FAISSVectorStore.load(
                    self.faiss_index_path, dimension=self.embedder.dimension
                )
                self.metadata_store = MetadataStore.load(self.metadata_path)
            except Exception as exc:
                logger.error(f"Failed to load existing index, starting empty: {exc}")

    @property
    def stats(self) -> Dict[str, Any]:
        return {
            "indexed_chunks": self.vector_store.count if self.vector_store else 0,
            "metadata_records": len(self.metadata_store),
            "index_path": str(self.faiss_index_path),
        }


_pipeline_singleton: RetrievalPipeline | None = None


def get_retrieval_pipeline() -> RetrievalPipeline:
    """Module-level singleton, so the FAISS index is loaded once per process."""
    global _pipeline_singleton
    if _pipeline_singleton is None:
        _pipeline_singleton = RetrievalPipeline()
    return _pipeline_singleton
