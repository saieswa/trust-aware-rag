"""
Text Chunking.

LLMs and embedding models both have limited context windows, and retrieval
works better on focused passages than entire documents — so every Document
gets split into smaller overlapping `Chunk`s before embedding.

We use character-based sliding-window chunking here (not token-based).
It's simpler, has zero extra dependencies, and is predictable — good enough
for this stage. Swapping in a token-aware chunker (e.g. using the actual
tokenizer of whatever LLM/embedding model we use) is a drop-in replacement
later, since everything downstream only depends on the `Chunk` shape.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List

from retrieval.loaders.document_loader import Document

DEFAULT_CHUNK_SIZE = 500      # characters per chunk
DEFAULT_CHUNK_OVERLAP = 50    # characters shared between consecutive chunks


@dataclass
class Chunk:
    """One retrievable unit of text, plus everything needed to trace it
    back to its source document for citation and trust scoring later."""

    chunk_id: str
    doc_id: str
    chunk_index: int
    text: str
    start_char: int
    end_char: int
    metadata: Dict[str, Any] = field(default_factory=dict)


def _snap_forward_to_word_boundary(text: str, pos: int) -> int:
    """
    Nudge `pos` forward until it lands at the start of a word (or end of
    text), so a chunk never begins mid-word.

    This matters specifically for the overlap step-back: `_split_text`
    computes the next chunk's start as `end - chunk_overlap`, a raw
    character offset with no awareness of word boundaries — left
    unadjusted, this reliably lands mid-word whenever the overlap size
    doesn't happen to fall exactly between two words.
    """
    n = len(text)
    while 0 < pos < n and text[pos - 1].isalnum() and text[pos].isalnum():
        pos += 1
    return pos


def _split_text(text: str, chunk_size: int, chunk_overlap: int) -> List[tuple[str, int, int]]:
    """
    Core sliding-window logic. Returns a list of (chunk_text, start, end)
    character-offset tuples.

    We try to break on a sentence or paragraph boundary near the target
    chunk_size instead of cutting mid-word, so chunks read naturally and
    a Critic/Verifier agent (added in a later step) doesn't have to reason
    about a sentence that's been sliced in half.
    """
    if chunk_overlap >= chunk_size:
        raise ValueError("chunk_overlap must be smaller than chunk_size.")

    spans: List[tuple[str, int, int]] = []
    text_length = len(text)
    start = 0

    while start < text_length:
        end = min(start + chunk_size, text_length)

        # If we're not at the very end of the text, try to end the chunk at
        # a nicer boundary (paragraph, then sentence, then space) within a
        # small search window, so we don't cut a sentence in half.
        if end < text_length:
            search_window = text[start:end]
            boundary = max(
                search_window.rfind("\n\n"),
                search_window.rfind(". "),
                search_window.rfind("\n"),
            )
            # Only use the boundary if it's not too close to the start
            # (otherwise chunks would become tiny).
            if boundary > chunk_size * 0.4:
                end = start + boundary + 1

        chunk_text = text[start:end].strip()
        if chunk_text:
            spans.append((chunk_text, start, end))

        if end >= text_length:
            break

        # Move the window forward, stepping back by chunk_overlap so
        # consecutive chunks share context — this helps retrieval when
        # the relevant sentence sits right at a chunk boundary. Snapped
        # forward to a word boundary so the next chunk never starts
        # mid-word (e.g. "lternative" instead of "alternative").
        start = _snap_forward_to_word_boundary(text, end - chunk_overlap)

    return spans


def chunk_document(
    document: Document,
    chunk_size: int = DEFAULT_CHUNK_SIZE,
    chunk_overlap: int = DEFAULT_CHUNK_OVERLAP,
) -> List[Chunk]:
    """Split one Document into a list of Chunks, carrying source metadata forward."""
    spans = _split_text(document.content, chunk_size, chunk_overlap)

    chunks: List[Chunk] = []
    for index, (text, start, end) in enumerate(spans):
        chunks.append(
            Chunk(
                chunk_id=f"{document.doc_id}_chunk{index}",
                doc_id=document.doc_id,
                chunk_index=index,
                text=text,
                start_char=start,
                end_char=end,
                metadata={
                    "source_title": document.title,
                    "source_path": document.source_path,
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
    """Chunk a whole batch of documents at once."""
    all_chunks: List[Chunk] = []
    for document in documents:
        all_chunks.extend(chunk_document(document, chunk_size, chunk_overlap))
    return all_chunks
