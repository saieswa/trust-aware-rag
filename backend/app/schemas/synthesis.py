"""
Pydantic schemas for the Synthesizer + Verifier pipeline API.
"""

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class SynthesisRequest(BaseModel):
    query: str = Field(..., min_length=1, examples=["Is it safe to combine Drug X and Drug Y?"])
    k: int = Field(default=5, ge=1, le=20)
    max_retries: int = Field(default=2, ge=0, le=5)
    trust_report: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Pre-computed trust report (e.g. from /trust/score). If omitted, runs the full Retriever+Critic+Trust pipeline first.",
    )


class CitationResponse(BaseModel):
    chunk_id: str
    source_title: str
    doc_id: str


class SentenceVerdictResponse(BaseModel):
    sentence: str
    verdict: str
    suggestion: Optional[str] = None


class SynthesisResponse(BaseModel):
    original_query: str
    status: str = Field(..., description="'approved', 'abstained', or 'verification_failed'.")
    final_answer: str
    citations: List[CitationResponse]
    synthesis_method: str = Field(..., description="'llm', 'heuristic', or 'abstained'.")
    verification_verdict: str
    verification_method: str
    hallucination_ratio: float
    sentence_verdicts: List[SentenceVerdictResponse]
    revision_suggestions: List[str]
    retry_count: int
    abstained: bool
    abstain_reason: Optional[str] = None
