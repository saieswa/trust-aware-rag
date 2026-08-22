"""
Metadata Storage with document scoping helpers.

Maps integer vector IDs to Chunk data (text, source document, character offsets,
section names, and document IDs).
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from loguru import logger


class MetadataStore:
    def __init__(self):
        self._store: Dict[int, Dict[str, Any]] = {}
        self._next_id: int = 0

    def next_id(self) -> int:
        """Hand out the next free integer ID, and advance the counter."""
        new_id = self._next_id
        self._next_id += 1
        return new_id

    def add(self, faiss_id: int, metadata: Dict[str, Any]) -> None:
        self._store[faiss_id] = metadata

    def get(self, faiss_id: int) -> Optional[Dict[str, Any]]:
        return self._store.get(faiss_id)

    def get_many(self, faiss_ids: list[int]) -> list[Dict[str, Any]]:
        return [self._store[i] for i in faiss_ids if i in self._store]

    def get_faiss_ids_for_doc(self, doc_id: str) -> List[int]:
        """Returns all integer FAISS IDs belonging strictly to doc_id."""
        return [
            fid for fid, record in self._store.items()
            if record.get("doc_id") == doc_id
        ]

    def get_distinct_doc_ids(self) -> List[str]:
        """Returns all unique document IDs present in the store."""
        seen = set()
        doc_ids = []
        for rec in self._store.values():
            d_id = rec.get("doc_id")
            if d_id and d_id not in seen:
                seen.add(d_id)
                doc_ids.append(d_id)
        return doc_ids

    def __len__(self) -> int:
        return len(self._store)

    def save(self, path: str | Path) -> None:
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "next_id": self._next_id,
            "records": {str(k): v for k, v in self._store.items()},
        }
        path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        logger.info(f"Metadata store saved to {path} ({len(self._store)} records).")

    @classmethod
    def load(cls, path: str | Path) -> "MetadataStore":
        store = cls()
        path = Path(path)
        if not path.exists():
            logger.warning(f"No metadata store found at {path}; starting empty.")
            return store

        payload = json.loads(path.read_text(encoding="utf-8"))
        store._next_id = payload.get("next_id", 0)
        store._store = {int(k): v for k, v in payload.get("records", {}).items()}
        logger.info(f"Metadata store loaded from {path} ({len(store)} records).")
        return store
