"""
Metadata Storage.

FAISS only stores vectors and integer IDs — it has no idea what text or
source document a vector came from. This module is the missing link: a
simple JSON-backed key-value store mapping each integer ID to the actual
`Chunk` data (text, source document, character offsets, etc.), so a search
result can be turned back into something a human (or the Critic Agent,
later) can actually read and cite.

For this project's scale (a demo/portfolio-sized document set), a JSON file
is a perfectly reasonable store. If this needs to scale to millions of
chunks later, this class's interface (`add`/`get`/`save`/`load`) is exactly
what you'd re-implement against PostgreSQL instead — nothing else in the
pipeline would need to change.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, Optional

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
