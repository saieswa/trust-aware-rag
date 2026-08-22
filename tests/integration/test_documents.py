"""
Integration tests for Document Ingestion, Parsing, and FAISS Vector Indexing.
"""

import json
from pathlib import Path
import pytest

from retrieval.loaders.document_loader import (
    load_document_from_bytes,
    extract_text_from_csv,
    extract_text_from_json,
    extract_text_from_docx,
    extract_text_from_pdf,
)
from retrieval.chunking.text_chunker import chunk_document
from retrieval.retriever import RetrievalPipeline


def test_txt_ingestion_and_chunking():
    content = b"Trust-Aware Multi-Agent RAG is a research framework for verifiable AI systems.\nIt uses calibrated trust scores."
    doc = load_document_from_bytes(content, "overview.txt")
    assert doc.doc_id.startswith("doc_")
    assert doc.title == "Trust-Aware Multi-Agent RAG is a research framework for verifiable AI systems."
    assert "Trust-Aware" in doc.content

    chunks = chunk_document(doc, chunk_size=100, chunk_overlap=20)
    assert len(chunks) >= 1
    assert chunks[0].metadata["filename"] == "overview.txt"
    assert chunks[0].metadata["file_type"] == "txt"


def test_csv_extraction():
    csv_bytes = b"name,role,department\nAlice,AI Engineer,Research\nBob,Security Lead,Infrastructure"
    text = extract_text_from_csv(csv_bytes)
    assert "Row 1: name: Alice, role: AI Engineer, department: Research." in text
    assert "Row 2: name: Bob, role: Security Lead, department: Infrastructure." in text

    doc = load_document_from_bytes(csv_bytes, "team.csv")
    assert doc.metadata["file_type"] == "csv"
    assert "Alice" in doc.content


def test_json_extraction():
    data = [
        {"id": "DOC-1", "title": "Retrieval Policy", "active": True},
        {"id": "DOC-2", "title": "Verification Rule", "active": False},
    ]
    json_bytes = json.dumps(data).encode("utf-8")
    text = extract_text_from_json(json_bytes)
    assert "Record 1: id: DOC-1; title: Retrieval Policy; active: True." in text

    doc = load_document_from_bytes(json_bytes, "policies.json")
    assert doc.metadata["file_type"] == "json"


def test_pipeline_index_and_search(tmp_path):
    pipeline = RetrievalPipeline()
    pipeline.faiss_index_path = tmp_path / "test_faiss.index"
    pipeline.metadata_path = tmp_path / "test_meta.json"

    content = b"The trust score threshold is set to 0.75 for high confidence answers and 0.50 for lower confidence."
    doc = load_document_from_bytes(content, "trust_policy.txt")

    chunk_count, chunk_details = pipeline.index_document(doc)
    assert chunk_count >= 1
    assert len(chunk_details) == chunk_count

    # Test Search
    results = pipeline.search("What is the trust score threshold?", k=3)
    assert len(results) >= 1
    assert doc.doc_id in [r.doc_id for r in results]
    assert results[0].doc_id == doc.doc_id
    assert "0.75" in results[0].text
    assert results[0].source_title == doc.title

    # Test Deletion
    deleted = pipeline.delete_document(doc.doc_id)
    assert deleted == chunk_count

    # Verify search no longer returns the deleted document
    post_delete_results = pipeline.search("What is the trust score threshold?", k=5)
    assert doc.doc_id not in [r.doc_id for r in post_delete_results]
