"""
Verifier Node 1 — Split Into Sentences.

Splitting is done here, once, as its own node — both the LLM path and the
heuristic fallback in Node 2 operate on the same sentence list, so the
splitting logic (and any edge cases in it) only has to be gotten right in
one place.
"""

from __future__ import annotations

import re
from typing import Any, Dict, List

from loguru import logger

from agents.state.synthesis_state import SynthesisVerificationState

# Splits on ". ", "! ", "? " followed by a capital letter or end of string —
# simple and dependency-free. Citation markers like "[chunk_id]" don't
# contain sentence-ending punctuation, so they stay attached to their
# sentence rather than being split off on their own.
_SENTENCE_SPLIT_PATTERN = re.compile(r"(?<=[.!?])\s+(?=[A-Z]|$)")


def _split_sentences(text: str) -> List[str]:
    sentences = [s.strip() for s in _SENTENCE_SPLIT_PATTERN.split(text.strip())]
    return [s for s in sentences if s]


def split_sentences(state: SynthesisVerificationState) -> Dict[str, Any]:
    """LangGraph node: reads `draft_answer`, writes `sentences`.

    Skipped (returns an empty list) if the Synthesizer already abstained —
    there's nothing to fact-check in a fixed "I don't have enough evidence"
    message."""
    if state.get("abstained"):
        return {"sentences": []}

    sentences = _split_sentences(state["draft_answer"])
    logger.info(f"Verifier: split draft answer into {len(sentences)} sentence(s).")
    return {"sentences": sentences}
