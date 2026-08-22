"""
Node 2 — Query Decomposition and Document-Aware Query Expansion.

Decomposes and expands user questions into targeted sub-queries. When `doc_id`
is present, it contextualizes queries with the specific document's metadata,
and handles metadata questions (e.g. title, authors) by targeting early chunks.
"""

from __future__ import annotations

import re
from typing import Any, Dict, List, Optional

from loguru import logger
from pydantic import BaseModel, Field

from agents.state.retriever_state import RetrieverState
from retrieval.retriever import get_retrieval_pipeline

MAX_SUB_QUERIES = 6

INTENT_TEMPLATES = [
    (
        re.compile(r"\b(?:what\s+is\s+(?:the\s+)?(?:title|name\s+of\s+this)|title\s+of\s+(?:the|this)\s+(?:paper|document))\b", re.I),
        [
            "{title} title document heading page 1",
            "{title} Abstract Introduction",
            "{title}",
        ],
    ),
    (
        re.compile(r"\b(?:who\s+(?:are\s+the\s+authors?|wrote|authored|is\s+the\s+author)|list\s+(?:the\s+)?authors?|authors?\s+of\s+(?:the|this))\b", re.I),
        [
            "{title} authors affiliations researchers page 1",
            "{title} Abstract Introduction authors",
            "{title}",
        ],
    ),
    (
        re.compile(r"\b(?:problem\s+statement|research\s+gap|motivation|challenge|issue|problem)\b", re.I),
        [
            "{title} problem statement research gap motivation challenge",
            "{title} Abstract Introduction main problem and contribution",
            "What is the problem statement of {title}?",
        ],
    ),
    (
        re.compile(r"\b(?:objective|goal|purpose|aim|contribution)\b", re.I),
        [
            "{title} main objective goal purpose contribution",
            "{title} Abstract Introduction proposed framework",
            "What is the main objective of {title}?",
        ],
    ),
    (
        re.compile(r"\b(?:method|methodology|approach|framework|architecture|algorithm|technique)\b", re.I),
        [
            "{title} method methodology proposed approach architecture algorithm",
            "{title} model overview empirical study workflow",
            "What methodology does {title} propose?",
        ],
    ),
    (
        re.compile(r"\b(?:results?|findings|performance|accuracy|benchmark|comparison|evaluation)\b", re.I),
        [
            "{title} experimental results performance evaluation findings",
            "{title} Table comparison benchmark metrics accuracy",
            "What are the main results of {title}?",
        ],
    ),
    (
        re.compile(r"\b(?:limitations?|drawbacks?|weakness|future\s+work)\b", re.I),
        [
            "{title} limitations drawbacks weaknesses future work discussion",
            "What are the limitations of {title}?",
        ],
    ),
    (
        re.compile(r"\b(?:conclusion|summary|takeaway)\b", re.I),
        [
            "{title} conclusion summary concluding remarks findings",
            "What is the conclusion of {title}?",
        ],
    ),
]


class SubQueryList(BaseModel):
    queries: List[str] = Field(
        description="1 to 3 focused search queries that together cover the original question."
    )


def _get_document_title_for_doc_id(doc_id: Optional[str]) -> Optional[str]:
    """Retrieves human-readable title for a specific document ID."""
    if not doc_id:
        return None
    try:
        pipeline = get_retrieval_pipeline()
        for _, rec in pipeline.metadata_store._store.items():
            if rec.get("doc_id") == doc_id:
                t = rec.get("source_title") or rec.get("filename")
                if t:
                    clean_t = re.sub(r"\.(pdf|txt|docx|csv|json|xlsx)$", "", t, flags=re.I)
                    return clean_t.replace("-", " ").replace("_", " ").strip()
        return None
    except Exception:
        return None


def _get_active_document_titles() -> List[str]:
    """Retrieves human-readable titles of currently indexed documents with PDF priority."""
    try:
        pipeline = get_retrieval_pipeline()
        titles = []
        for _, rec in pipeline.metadata_store._store.items():
            t = rec.get("source_title") or rec.get("filename")
            if t and t not in ("Unknown Source", ""):
                clean_t = re.sub(r"\.(pdf|txt|docx|csv|json|xlsx)$", "", t, flags=re.I)
                clean_t = clean_t.replace("-", " ").replace("_", " ").strip()
                if clean_t not in titles:
                    if rec.get("file_type") == "pdf" or "paper" in t.lower() or "redeep" in t.lower():
                        titles.insert(0, clean_t)
                    else:
                        titles.append(clean_t)
        return titles
    except Exception:
        return []


def _expand_domain_intents(query: str, primary_title: str) -> List[str]:
    expanded: List[str] = [query]

    paper_ref_pattern = re.compile(r"\b(?:this|the)\s+(?:paper|document|study|article|research)\b", re.I)
    if paper_ref_pattern.search(query):
        contextualized_q = paper_ref_pattern.sub(primary_title, query)
        if contextualized_q not in expanded:
            expanded.append(contextualized_q)

    for pattern, templates in INTENT_TEMPLATES:
        if pattern.search(query):
            for tpl in templates:
                formatted = tpl.format(title=primary_title)
                if formatted not in expanded:
                    expanded.append(formatted)

    return expanded


def decompose_query(state: RetrieverState) -> Dict[str, Any]:
    query = state["original_query"]
    doc_id = state.get("doc_id")

    primary_title = _get_document_title_for_doc_id(doc_id)
    if not primary_title:
        all_titles = _get_active_document_titles()
        primary_title = all_titles[0] if all_titles else "the document"

    sub_queries = _expand_domain_intents(query, primary_title)
    method = "contextual_domain_expansion"

    if query in sub_queries:
        sub_queries.remove(query)
    sub_queries.insert(0, query)

    seen = set()
    cleaned = []
    for q in sub_queries:
        k = q.strip().lower()
        if k and k not in seen:
            seen.add(k)
            cleaned.append(q.strip())
        if len(cleaned) == MAX_SUB_QUERIES:
            break

    logger.info(f"[RETRIEVAL] Sub-queries for doc_id={doc_id!r} ({method}): {cleaned}")
    return {"sub_queries": cleaned or [query], "decomposition_method": method}
