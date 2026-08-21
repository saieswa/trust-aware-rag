"""
Pydantic schemas for the Retriever Agent API.

Deliberately exposes the *intermediate* pipeline details (sub-queries used,
decomposition method, dedup counts) in the response, not just the final
evidence list — this is what makes the agent auditable rather than a black
box, which is the whole point of the project.
"""

from typing import List

from pydantic import BaseModel, Field


class RetrieverAgentRequest(BaseModel):
    query: str = Field(..., min_length=1, examples=["What is the refund policy and shipping cost for late deliveries?"])
    k: int = Field(default=5, ge=1, le=20, description="Number of top evidence chunks to return.")


class EvidenceChunkResponse(BaseModel):
    chunk_id: str
    doc_id: str
    text: str
    score: float = Field(..., description="Raw FAISS similarity score.")
    final_rank_score: float = Field(..., description="Similarity score plus cross-query agreement bonus.")
    source_title: str
    source_path: str
    chunk_index: int
    matched_sub_queries: List[str] = Field(
        ..., description="Which decomposed sub-quer(y/ies) retrieved this chunk."
    )


class RetrieverAgentResponse(BaseModel):
    original_query: str
    sub_queries: List[str]
    decomposition_method: str = Field(..., description="'llm', 'heuristic', or 'none'.")
    total_candidates_before_dedup: int
    total_candidates_after_dedup: int
    top_evidence: List[EvidenceChunkResponse]
