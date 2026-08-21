"""
Node 1 — Read Retrieved Documents.

This node's only job is to take whatever the Retriever Agent (or a direct
API caller) handed us and turn it into a clean, validated list the rest of
the Critic Agent can rely on — deduplicated by chunk_id (defensive, in case
the caller passes raw pre-dedup results), with any chunk missing usable
text dropped, and a `word_count` precomputed since two later nodes both
need it.
"""

from __future__ import annotations

from typing import Any, Dict

from loguru import logger

from agents.state.critic_state import CriticState


def read_evidence(state: CriticState) -> Dict[str, Any]:
    """LangGraph node: reads `evidence`, writes `normalized_evidence`."""
    raw_evidence = state.get("evidence", [])

    seen_ids = set()
    normalized = []
    for item in raw_evidence:
        chunk_id = item.get("chunk_id")
        text = (item.get("text") or "").strip()
        if not chunk_id or not text or chunk_id in seen_ids:
            continue
        seen_ids.add(chunk_id)
        normalized.append({**item, "text": text, "word_count": len(text.split())})

    logger.info(f"Critic Agent read {len(normalized)} evidence chunk(s) (from {len(raw_evidence)} input).")
    return {"normalized_evidence": normalized}
