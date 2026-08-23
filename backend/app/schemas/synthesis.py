"""
Pydantic schemas for the Synthesizer + Verifier pipeline API.
"""

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class SynthesisRequest(BaseModel):
    query: str = Field(..., min_length=1, examples=["Is it safe to combine Drug X and Drug Y?"])
    k: int = Field(default=5, ge=1, le=20)
    max_retries: int = Field(default=2, ge=0, le=5)
    doc_id: Optional[str] = Field(default=None, description="Active document ID to scope retrieval and synthesis.")
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


class StructuredEvidenceItem(BaseModel):
    page: Optional[int] = 1
    text: str
    source: str
    chunk_id: Optional[str] = None


class StructuredAnswer(BaseModel):
    answer_type: str = Field(default="document_explanation", description="'document_explanation', 'specific_answer', or 'abstention'")
    document_overview: Optional[str] = None
    main_idea: Optional[str] = None
    steps: List[str] = Field(default_factory=list)
    key_points: List[str] = Field(default_factory=list)
    main_findings: List[str] = Field(default_factory=list)
    simple_explanation: Optional[str] = None
    direct_answer: Optional[str] = None
    evidence: List[StructuredEvidenceItem] = Field(default_factory=list)


class SynthesisResponse(BaseModel):
    original_query: str
    doc_id: Optional[str] = None
    status: str = Field(..., description="'approved', 'abstained', or 'verification_failed'.")
    final_answer: str
    structured_answer: Optional[StructuredAnswer] = None
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
