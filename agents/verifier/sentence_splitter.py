"""
Verifier Node 1 — Split Into Sentences.

Splits draft answers into checkable sentences and bullet claims, filtering
out markdown structure headings, metadata, and evidence quote blocks.
"""

from __future__ import annotations

import re
from typing import Any, Dict, List

from loguru import logger

from agents.state.synthesis_state import SynthesisVerificationState

_SENTENCE_SPLIT_PATTERN = re.compile(r"(?<=[.!?])\s+(?=[A-Z]|$)")


def _split_sentences(text: str) -> List[str]:
    raw_lines = text.strip().split("\n")
    sentences: List[str] = []
    current_section = ""

    for line in raw_lines:
        line_clean = line.strip()
        if not line_clean:
            continue

        if line_clean.startswith("#"):
            current_section = line_clean.lower()
            continue

        # Skip quote blocks or metadata blocks under Evidence, Evidence Used, or Source
        if any(sec in current_section for sec in ["evidence", "source", "trust"]):
            continue

        if line_clean.lower().startswith(("source:", "trust score:", "trust:", "evidence:")):
            continue

        # Handle bullet points
        if line_clean.startswith(("-", "*", "•")):
            bullet_text = re.sub(r"^[-*•]\s*", "", line_clean).strip()
            if bullet_text and len(bullet_text) > 3:
                sentences.append(bullet_text)
            continue

        # Normal text paragraph splitting
        split_pieces = [s.strip() for s in _SENTENCE_SPLIT_PATTERN.split(line_clean) if s.strip()]
        for piece in split_pieces:
            if len(piece) > 5:
                sentences.append(piece)

    return sentences


def split_sentences(state: SynthesisVerificationState) -> Dict[str, Any]:
    """LangGraph node: reads `draft_answer`, writes `sentences`."""
    if state.get("abstained"):
        return {"sentences": []}

    sentences = _split_sentences(state["draft_answer"])
    logger.info(f"Verifier: split draft answer into {len(sentences)} substantive claim sentence(s).")
    return {"sentences": sentences}
