"""
Retriever Pipeline with Strict In-Engine FAISS Document Scoping.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

from loguru import logger

from retrieval.chunking.text_chunker import chunk_document
from retrieval.embeddings.embedding_model import HuggingFaceEmbedder, get_embedder
from retrieval.loaders.document_loader import (
    Document,
    load_documents_from_directory,
)
from retrieval.vector_store.faiss_store import FAISSVectorStore
from retrieval.vector_store.metadata_store import MetadataStore

DEFAULT_INDEX_PATH = "models/embeddings_cache/faiss_index.index"
DEFAULT_METADATA_PATH = "models/embeddings_cache/faiss_index.meta.json"


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
    def __init__(
        self,
        index_path: str = DEFAULT_INDEX_PATH,
        metadata_path: str = DEFAULT_METADATA_PATH,
        embed_model_name: Optional[str] = None,
    ):
        self.index_path = index_path
        self.metadata_path = metadata_path
        self.embedder = HuggingFaceEmbedder(embed_model_name) if embed_model_name else get_embedder()

        self.vector_store: Optional[FAISSVectorStore] = None
        self.metadata_store: Optional[MetadataStore] = None

        self._load_or_init()

    # ---------------------------------------------------------------- #
    # Indexing
    # ---------------------------------------------------------------- #

    def index_document(
        self,
        doc: Document,
        chunk_size: int = 500,
        chunk_overlap: int = 50,
    ) -> tuple[int, List[Dict[str, Any]]]:
        if not doc.content.strip():
            logger.warning(f"Document {doc.doc_id} ('{doc.title}') has empty text, skipping.")
            return 0, []

        chunks = chunk_document(doc, chunk_size=chunk_size, chunk_overlap=chunk_overlap)
        if not chunks:
            logger.warning(f"No chunks created for {doc.doc_id}.")
            return 0, []

        texts = [c.text for c in chunks]
        embeddings = self.embedder.embed(texts)

        if self.vector_store is None:
            self.vector_store = FAISSVectorStore(dimension=self.embedder.dimension)
        if self.metadata_store is None:
            self.metadata_store = MetadataStore()

        chunk_details: List[Dict[str, Any]] = []
        faiss_ids: List[int] = []
        for chunk in chunks:
            faiss_id = self.metadata_store.next_id()
            metadata = {
                "chunk_id": chunk.chunk_id,
                "doc_id": chunk.doc_id,
                "source_title": doc.title,
                "source_path": doc.source_path,
                "source_url": getattr(doc, "source_url", None),
                "text": chunk.text,
                "chunk_index": chunk.chunk_index,
                "section": chunk.section,
                "page_number": chunk.page_number,
                "file_type": doc.metadata.get("file_type", "txt"),
            }
            self.metadata_store.add(faiss_id, metadata)
            faiss_ids.append(faiss_id)

            chunk_details.append(
                {
                    "chunk_id": chunk.chunk_id,
                    "faiss_id": faiss_id,
                    "chunk_index": chunk.chunk_index,
                    "page_number": chunk.page_number,
                    "section": chunk.section,
                    "text": chunk.text,
                }
            )

        self.vector_store.add(embeddings, faiss_ids)
        self._persist()

        logger.info(
            f"Indexed document {doc.doc_id} ('{doc.title}') into {len(chunks)} chunk(s). "
            f"Embed dimension={self.embedder.dimension}, Total index vectors={self.vector_store.count}."
        )
        return len(chunks), chunk_details

    def index_directory(
        self,
        directory: str = "data/sample_documents",
        chunk_size: int = 500,
        chunk_overlap: int = 50,
    ) -> Dict[str, Any]:
        path = Path(directory)
        if not path.is_dir():
            raise ValueError(f"Directory not found: {directory}")

        documents = load_documents_from_directory(directory)
        if not documents:
            return {"documents_indexed": 0, "chunks_indexed": 0, "message": "No documents found."}

        self.vector_store = FAISSVectorStore(dimension=self.embedder.dimension)
        self.metadata_store = MetadataStore()

        total_chunks = 0
        for doc in documents:
            chunks_indexed, _ = self.index_document(doc, chunk_size, chunk_overlap)
            total_chunks += chunks_indexed

        return {
            "documents_indexed": len(documents),
            "chunks_indexed": total_chunks,
            "message": f"Successfully indexed {len(documents)} document(s).",
        }

    def delete_document(self, doc_id: str) -> bool:
        """Purges vectors and metadata for a document and persists index."""
        if self.metadata_store is None or self.vector_store is None:
            return False

        retained_records = [
            rec for rec in self.metadata_store._store.values()
            if rec.get("doc_id") != doc_id
        ]

        # Reconstruct clean store without deleted doc
        self.vector_store = FAISSVectorStore(dimension=self.embedder.dimension)
        self.metadata_store = MetadataStore()

        if retained_records:
            texts = [r["text"] for r in retained_records]
            embeddings = self.embedder.embed(texts)
            faiss_ids = []
            for rec in retained_records:
                fid = self.metadata_store.next_id()
                self.metadata_store.add(fid, rec)
                faiss_ids.append(fid)
            self.vector_store.add(embeddings, faiss_ids)

        self._persist()
        logger.info(f"Deleted document {doc_id} from vector store. Remaining vectors: {self.vector_store.count}")
        return True

    # ---------------------------------------------------------------- #
    # Search
    # ---------------------------------------------------------------- #

    def search(self, query: str, k: int = 5, doc_id: Optional[str] = None) -> List[RetrievedChunk]:
        if self.vector_store is None or self.vector_store.count == 0 or self.metadata_store is None:
            logger.warning("Search called before any documents were indexed.")
            return []

        allowed_ids = None
        if doc_id:
            allowed_ids = self.metadata_store.get_faiss_ids_for_doc(doc_id)
            if not allowed_ids:
                logger.info(f"[RETRIEVAL] No chunks found in metadata store for doc_id={doc_id!r}. Returning empty.")
                return []

        query_vector = self.embedder.embed([query])[0]
        ids, scores = self.vector_store.search(query_vector, k=k, allowed_ids=allowed_ids)

        retrieved_doc_ids = set()
        valid_chunks: List[RetrievedChunk] = []
        invalid_count = 0

        for faiss_id, score in zip(ids, scores):
            meta = self.metadata_store.get(faiss_id)
            if meta is None:
                continue

            chunk_doc_id = meta.get("doc_id")
            retrieved_doc_ids.add(chunk_doc_id)

            if doc_id and chunk_doc_id != doc_id:
                invalid_count += 1
                logger.error(
                    f"DOCUMENT ISOLATION ERROR: Retrieved chunk {meta.get('chunk_id')} "
                    f"has doc_id={chunk_doc_id!r}, expected active_doc_id={doc_id!r}."
                )
                continue

            valid_chunks.append(
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

        logger.info(
            f"\n========================================\n"
            f"ACTIVE DOCUMENT:\n{doc_id or 'ALL_DOCUMENTS'}\n\n"
            f"QUERY:\n{query}\n\n"
            f"RETRIEVED DOCUMENT IDS:\n{list(retrieved_doc_ids)}\n\n"
            f"VALID CHUNKS:\n{len(valid_chunks)}\n\n"
            f"INVALID CHUNKS:\n{invalid_count}\n\n"
            f"ANSWER SOURCE:\n{doc_id or 'GLOBAL'}\n"
            f"========================================"
        )

        return valid_chunks

    # ---------------------------------------------------------------- #
    # Persistence helpers
    # ---------------------------------------------------------------- #

    def _persist(self) -> None:
        if self.vector_store is not None:
            self.vector_store.save(self.index_path)
        if self.metadata_store is not None:
            self.metadata_store.save(self.metadata_path)

    def _save(self) -> None:
        self._persist()

    def _load_or_init(self) -> None:
        idx_p = Path(self.index_path)
        meta_p = Path(self.metadata_path)

        if idx_p.exists() and meta_p.exists():
            try:
                self.vector_store = FAISSVectorStore.load(self.index_path, dimension=self.embedder.dimension)
                self.metadata_store = MetadataStore.load(self.metadata_path)
                return
            except Exception as exc:
                logger.warning(f"Could not load cached index ({exc}). Initializing empty index.")

        self.vector_store = FAISSVectorStore(dimension=self.embedder.dimension)
        self.metadata_store = MetadataStore()

    @property
    def stats(self) -> Dict[str, Any]:
        return {
            "indexed_chunks": self.vector_store.count if self.vector_store else 0,
            "metadata_records": self.metadata_store.count if self.metadata_store else 0,
            "index_path": self.index_path,
        }


_pipeline_singleton: Optional[RetrievalPipeline] = None


def get_retrieval_pipeline() -> RetrievalPipeline:
    global _pipeline_singleton
    if _pipeline_singleton is None:
        _pipeline_singleton = RetrievalPipeline()
    return _pipeline_singleton
