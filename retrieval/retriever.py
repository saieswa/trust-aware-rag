"""
Retrieval Pipeline.

Wires together document loader, section-aware chunker, sentence-transformer
embedder, FAISS vector store, and metadata store.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from loguru import logger

from app.core.config import get_settings
from retrieval.chunking.text_chunker import Chunk, chunk_document, chunk_documents
from retrieval.embeddings.embedding_model import EmbeddingModel, get_embedder
from retrieval.loaders.document_loader import Document, load_documents_from_directory
from retrieval.vector_store.faiss_store import FAISSVectorStore
from retrieval.vector_store.metadata_store import MetadataStore


@dataclass
class RetrievedChunk:
    chunk_id: str
    doc_id: str
    text: str
    score: float
    source_title: str
    source_path: str
    chunk_index: int
    section: str = "General"
    page_number: Optional[int] = None


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
    # Incremental Indexing
    # ---------------------------------------------------------------- #

    def index_document(
        self,
        document: Document,
        chunk_size: int = 800,
        chunk_overlap: int = 100,
    ) -> Tuple[int, List[Dict[str, Any]]]:
        """Indexes a single document into FAISS with enriched section embeddings."""
        self.delete_document(document.doc_id, persist=False)

        chunks: List[Chunk] = chunk_document(document, chunk_size, chunk_overlap)
        if not chunks:
            logger.warning(f"No chunks produced for document {document.doc_id}")
            return 0, []

        # Embed enriched contextual text (includes Document Title, Section, and Page Number)
        texts_to_embed = [c.embed_text for c in chunks]
        vectors = self.embedder.embed(texts_to_embed)

        if self.vector_store is None:
            self.vector_store = FAISSVectorStore(dimension=self.embedder.dimension)

        ids = []
        chunk_details: List[Dict[str, Any]] = []

        for chunk in chunks:
            faiss_id = self.metadata_store.next_id()
            ids.append(faiss_id)

            meta_record = {
                "chunk_id": chunk.chunk_id,
                "doc_id": chunk.doc_id,
                "text": chunk.text,
                "chunk_index": chunk.chunk_index,
                "section": chunk.section,
                "page_number": chunk.page_number,
                "source_title": chunk.metadata.get("source_title", document.title),
                "source_path": chunk.metadata.get("source_path", document.source_path),
                "source_type": chunk.metadata.get("source_type", "file"),
                "source_url": chunk.metadata.get("source_url"),
                "file_type": chunk.metadata.get("file_type", "txt"),
                "filename": chunk.metadata.get("filename", document.title),
            }

            self.metadata_store.add(faiss_id, meta_record)
            chunk_details.append({"faiss_id": faiss_id, "chunk": chunk, "metadata": meta_record})

        self.vector_store.add(vectors, ids)
        self._persist()

        logger.info(
            f"Indexed document {document.doc_id} ('{document.title}') into {len(chunks)} chunk(s). "
            f"Embed dimension={self.embedder.dimension}, Total index vectors={self.vector_store.count}."
        )
        return len(chunks), chunk_details

    # ---------------------------------------------------------------- #
    # Deletion & Rebuilding
    # ---------------------------------------------------------------- #

    def delete_document(self, doc_id: str, persist: bool = True) -> int:
        faiss_ids_to_remove = [
            fid for fid, record in self.metadata_store._store.items()
            if record.get("doc_id") == doc_id
        ]

        if not faiss_ids_to_remove:
            return 0

        for fid in faiss_ids_to_remove:
            self.metadata_store._store.pop(fid, None)

        remaining_records = list(self.metadata_store._store.items())
        self.vector_store = FAISSVectorStore(dimension=self.embedder.dimension)

        if remaining_records:
            remaining_ids = [fid for fid, _ in remaining_records]
            # Embed with contextual section headers
            remaining_texts = []
            for _, rec in remaining_records:
                doc_title = rec.get("source_title", "")
                section = rec.get("section", "")
                page = rec.get("page_number")
                prefix = []
                if doc_title:
                    prefix.append(f"Document: {doc_title}")
                if section and section != "General":
                    prefix.append(f"Section: {section}")
                if page:
                    prefix.append(f"Page: {page}")
                header = f"[{' | '.join(prefix)}]\n" if prefix else ""
                remaining_texts.append(header + rec.get("text", ""))

            remaining_vectors = self.embedder.embed(remaining_texts)
            self.vector_store.add(remaining_vectors, remaining_ids)

        if persist:
            self._persist()

        logger.info(f"Deleted document {doc_id} ({len(faiss_ids_to_remove)} chunks removed).")
        return len(faiss_ids_to_remove)

    # ---------------------------------------------------------------- #
    # Directory & Batch Indexing
    # ---------------------------------------------------------------- #

    def index_directory(
        self,
        directory: str | Path,
        chunk_size: int = 800,
        chunk_overlap: int = 100,
    ) -> Dict[str, Any]:
        documents = load_documents_from_directory(directory)
        if not documents:
            return {"documents_indexed": 0, "chunks_indexed": 0, "message": "No documents found."}

        total_chunks = 0
        for doc in documents:
            chunks_indexed, _ = self.index_document(doc, chunk_size, chunk_overlap)
            total_chunks += chunks_indexed

        return {
            "documents_indexed": len(documents),
            "chunks_indexed": total_chunks,
            "message": f"Successfully indexed {len(documents)} document(s).",
        }

    # ---------------------------------------------------------------- #
    # Search
    # ---------------------------------------------------------------- #

    def search(self, query: str, k: int = 5) -> List[RetrievedChunk]:
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
                    score=round(float(score), 4),
                    source_title=meta.get("source_title", "Unknown Source"),
                    source_path=meta.get("source_path", meta.get("source_url", "")),
                    chunk_index=meta.get("chunk_index", 0),
                    section=meta.get("section", "General"),
                    page_number=meta.get("page_number"),
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
    global _pipeline_singleton
    if _pipeline_singleton is None:
        _pipeline_singleton = RetrievalPipeline()
    return _pipeline_singleton
