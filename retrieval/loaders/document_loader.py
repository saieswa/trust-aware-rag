"""
Document Loader.

This is the very first stage of the retrieval pipeline: turning raw files
on disk into a consistent in-memory shape (`Document`) that the rest of the
pipeline (chunker, embedder, vector store) can work with, regardless of
where the file came from or what it looked like originally.

Right now it supports plain `.txt` and `.md` files, which is enough for the
sample_documents/ set. Adding PDF/DOCX support later means adding a new
`_read_*` function here — nothing downstream needs to change, because
everything downstream only ever sees a `Document`.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List

from loguru import logger

# File extensions this loader currently knows how to read.
SUPPORTED_EXTENSIONS = {".txt", ".md"}


@dataclass
class Document:
    """
    One fully-loaded source document.

    `doc_id` is derived deterministically from the file path (see
    `_make_doc_id`), so re-indexing the same file always produces the same
    ID instead of a random one — that matters once we want to support
    "re-index this one file" without duplicating it in the vector store.
    """

    doc_id: str
    source_path: str
    title: str
    content: str
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def char_count(self) -> int:
        return len(self.content)


def _make_doc_id(path: Path) -> str:
    """
    Deterministic ID from the file's absolute path.

    We hash the path (not the content) so the ID stays stable even if the
    file's text is edited slightly — it's still "the same document" from
    the pipeline's point of view. Using the first 12 hex characters keeps
    IDs short but collision-unlikely for a project-sized document set.
    """
    digest = hashlib.sha256(str(path.resolve()).encode("utf-8")).hexdigest()
    return f"doc_{digest[:12]}"


def _derive_title(path: Path, content: str) -> str:
    """
    Use the first non-empty line as a title if it looks like one (short,
    no trailing period), otherwise fall back to the filename. This keeps
    loading simple — no special frontmatter syntax required in the source
    files themselves.
    """
    first_line = next((line.strip() for line in content.splitlines() if line.strip()), "")
    if first_line and len(first_line) < 120:
        return first_line
    return path.stem.replace("_", " ").title()


def load_document(path: Path) -> Document:
    """Load a single file into a Document."""
    content = path.read_text(encoding="utf-8", errors="replace").strip()
    return Document(
        doc_id=_make_doc_id(path),
        source_path=str(path),
        title=_derive_title(path, content),
        content=content,
        metadata={
            "filename": path.name,
            "extension": path.suffix,
            "size_bytes": path.stat().st_size,
        },
    )


def load_documents_from_directory(directory: str | Path) -> List[Document]:
    """
    Load every supported file in a directory (non-recursive by default).

    Returns an empty list — not an error — if the directory has no
    supported files, since "nothing to index yet" is a normal state early
    in a project, not a failure.
    """
    directory = Path(directory)
    if not directory.exists():
        logger.warning(f"Document directory does not exist: {directory}")
        return []

    documents: List[Document] = []
    for path in sorted(directory.iterdir()):
        if path.is_file() and path.suffix.lower() in SUPPORTED_EXTENSIONS:
            try:
                documents.append(load_document(path))
            except Exception as exc:
                logger.error(f"Failed to load document {path}: {exc}")

    logger.info(f"Loaded {len(documents)} document(s) from {directory}")
    return documents
