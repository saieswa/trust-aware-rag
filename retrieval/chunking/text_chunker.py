"""
Semantic and Section-Aware Text Chunking.

Splits documents into coherent, paragraph-aligned passages tagged with
document title, page number, and detected section headers (Abstract,
Introduction, Methodology, Experiments, Conclusion, Appendix, etc.).
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from retrieval.loaders.document_loader import Document, detect_section_header, _clean_page_text

DEFAULT_CHUNK_SIZE = 800      # characters per chunk (~120-150 words)
DEFAULT_CHUNK_OVERLAP = 100   # overlap characters


@dataclass
class Chunk:
    chunk_id: str
    doc_id: str
    chunk_index: int
    text: str
    start_char: int
    end_char: int
    section: str = "General"
    page_number: Optional[int] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def embed_text(self) -> str:
        """Enriched text representation for semantic vector embedding."""
        prefix_parts = []
        if self.metadata.get("source_title"):
            prefix_parts.append(f"Document: {self.metadata['source_title']}")
        if self.section and self.section != "General":
            prefix_parts.append(f"Section: {self.section}")
        if self.page_number:
            prefix_parts.append(f"Page: {self.page_number}")

        if prefix_parts:
            return f"[{' | '.join(prefix_parts)}]\n{self.text}"
        return self.text


def _split_into_paragraphs(text: str) -> List[str]:
    paras = [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]
    return paras or [text.strip()]


def chunk_document(
    document: Document,
    chunk_size: int = DEFAULT_CHUNK_SIZE,
    chunk_overlap: int = DEFAULT_CHUNK_OVERLAP,
) -> List[Chunk]:
    chunks: List[Chunk] = []
    chunk_counter = 0
    current_section = "Abstract / Overview"

    # Multi-page documents (PDFs)
    if getattr(document, "pages", None) and len(document.pages) > 0:
        for page_info in document.pages:
            p_num = page_info.get("page_number", 1)
            raw_text = page_info.get("text", "")
            p_text = _clean_page_text(raw_text)
            if not p_text.strip():
                continue

            paragraphs = _split_into_paragraphs(p_text)
            current_buffer: List[str] = []
            current_len = 0

            for para in paragraphs:
                # Detect any section transition in this paragraph
                for line in para.splitlines():
                    detected = detect_section_header(line)
                    if detected:
                        if current_buffer:
                            chunk_text = " ".join(current_buffer).strip()
                            if chunk_text:
                                chunks.append(
                                    Chunk(
                                        chunk_id=f"{document.doc_id}_chunk{chunk_counter}",
                                        doc_id=document.doc_id,
                                        chunk_index=chunk_counter,
                                        text=chunk_text,
                                        start_char=0,
                                        end_char=len(chunk_text),
                                        section=current_section,
                                        page_number=p_num,
                                        metadata={
                                            "source_title": document.title,
                                            "source_path": document.source_path,
                                            "section": current_section,
                                            "page_number": p_num,
                                            **document.metadata,
                                        },
                                    )
                                )
                                chunk_counter += 1
                            current_buffer = []
                            current_len = 0
                        current_section = detected
                        break

                if current_len + len(para) > chunk_size and current_buffer:
                    chunk_text = " ".join(current_buffer).strip()
                    if chunk_text:
                        chunks.append(
                            Chunk(
                                chunk_id=f"{document.doc_id}_chunk{chunk_counter}",
                                doc_id=document.doc_id,
                                chunk_index=chunk_counter,
                                text=chunk_text,
                                start_char=0,
                                end_char=len(chunk_text),
                                section=current_section,
                                page_number=p_num,
                                metadata={
                                    "source_title": document.title,
                                    "source_path": document.source_path,
                                    "section": current_section,
                                    "page_number": p_num,
                                    **document.metadata,
                                },
                            )
                        )
                        chunk_counter += 1
                    current_buffer = [para]
                    current_len = len(para)
                else:
                    current_buffer.append(para)
                    current_len += len(para)

            # Flush end of page
            if current_buffer:
                chunk_text = " ".join(current_buffer).strip()
                if chunk_text:
                    chunks.append(
                        Chunk(
                            chunk_id=f"{document.doc_id}_chunk{chunk_counter}",
                            doc_id=document.doc_id,
                            chunk_index=chunk_counter,
                            text=chunk_text,
                            start_char=0,
                            end_char=len(chunk_text),
                            section=current_section,
                            page_number=p_num,
                            metadata={
                                "source_title": document.title,
                                "source_path": document.source_path,
                                "section": current_section,
                                "page_number": p_num,
                                **document.metadata,
                            },
                        )
                    )
                    chunk_counter += 1

        if chunks:
            return chunks

    # Single-page / Plain text documents
    cleaned_content = _clean_page_text(document.content)
    paragraphs = _split_into_paragraphs(cleaned_content)
    current_buffer = []
    current_len = 0

    for para in paragraphs:
        for line in para.splitlines():
            detected = detect_section_header(line)
            if detected:
                if current_buffer:
                    chunk_text = " ".join(current_buffer).strip()
                    if chunk_text:
                        chunks.append(
                            Chunk(
                                chunk_id=f"{document.doc_id}_chunk{chunk_counter}",
                                doc_id=document.doc_id,
                                chunk_index=chunk_counter,
                                text=chunk_text,
                                start_char=0,
                                end_char=len(chunk_text),
                                section=current_section,
                                page_number=None,
                                metadata={
                                    "source_title": document.title,
                                    "source_path": document.source_path,
                                    "section": current_section,
                                    "page_number": None,
                                    **document.metadata,
                                },
                            )
                        )
                        chunk_counter += 1
                    current_buffer = []
                    current_len = 0
                current_section = detected
                break

        if current_len + len(para) > chunk_size and current_buffer:
            chunk_text = " ".join(current_buffer).strip()
            if chunk_text:
                chunks.append(
                    Chunk(
                        chunk_id=f"{document.doc_id}_chunk{chunk_counter}",
                        doc_id=document.doc_id,
                        chunk_index=chunk_counter,
                        text=chunk_text,
                        start_char=0,
                        end_char=len(chunk_text),
                        section=current_section,
                        page_number=None,
                        metadata={
                            "source_title": document.title,
                            "source_path": document.source_path,
                            "section": current_section,
                            "page_number": None,
                            **document.metadata,
                        },
                    )
                )
                chunk_counter += 1
            current_buffer = [para]
            current_len = len(para)
        else:
            current_buffer.append(para)
            current_len += len(para)

    if current_buffer:
        chunk_text = " ".join(current_buffer).strip()
        if chunk_text:
            chunks.append(
                Chunk(
                    chunk_id=f"{document.doc_id}_chunk{chunk_counter}",
                    doc_id=document.doc_id,
                    chunk_index=chunk_counter,
                    text=chunk_text,
                    start_char=0,
                    end_char=len(chunk_text),
                    section=current_section,
                    page_number=None,
                    metadata={
                        "source_title": document.title,
                        "source_path": document.source_path,
                        "section": current_section,
                        "page_number": None,
                        **document.metadata,
                    },
                )
            )

    return chunks


def chunk_documents(
    documents: List[Document],
    chunk_size: int = DEFAULT_CHUNK_SIZE,
    chunk_overlap: int = DEFAULT_CHUNK_OVERLAP,
) -> List[Chunk]:
    all_chunks: List[Chunk] = []
    for document in documents:
        all_chunks.extend(chunk_document(document, chunk_size, chunk_overlap))
    return all_chunks
