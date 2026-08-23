/**
 * Shared types mirroring the backend's Pydantic schemas
 * (backend/app/schemas/*.py).
 */

export type Decision = "answer" | "retrieve_more" | "abstain";
export type EvidenceLabel = "support" | "contradict" | "neutral";
export type SynthesisStatus = "approved" | "abstained" | "verification_failed";

export interface FeatureDetail {
  value: number;
  weight: number;
  contribution: number;
  applied_as?: string | null;
}

export interface TrustReportResponse {
  query: string;
  trust_score: number;
  decision: Decision;
  feature_breakdown: Record<string, FeatureDetail>;
  diagnostics: {
    evidence_count: number;
    support_count: number;
    distinct_source_count: number;
    contradiction_count: number;
  };
  contradictions: Array<{
    chunk_id_a: string;
    chunk_id_b: string;
    explanation: string;
  }>;
  contradiction_method: string;
  labeling_method: string;
  evidence: ScoredEvidence[];
}

export interface ScoredEvidence {
  chunk_id: string;
  doc_id: string;
  source_title: string;
  text: string;
  label: EvidenceLabel;
  reasoning: string;
  score: number;
  final_rank_score: number;
  specificity_score: number;
  source_reliability_score: number;
  quality_score: number;
}

export interface EvaluationHistoryItem {
  id: string;
  query: string;
  doc_id?: string | null;
  document_name: string;
  decision: Decision | string;
  trust_score: number;
  created_at: string;
  final_answer?: string | null;
}

export interface DocumentPerformanceItem {
  doc_id: string;
  document_name: string;
  total_queries: number;
  average_trust_score: number;
  supported_count: number;
  needs_more_evidence_count: number;
  abstained_count: number;
}

export interface TrustDashboardResponse {
  total_queries: number;
  average_trust_score: number;
  decision_counts: Record<Decision, number>;
  average_contradiction_score: number;
  average_agreement_score: number;
  llm_usage_rate: number;
  history: EvaluationHistoryItem[];
  document_performance: DocumentPerformanceItem[];
}

export interface CitationResponse {
  chunk_id: string;
  source_title: string;
  doc_id: string;
}

export interface SentenceVerdictResponse {
  sentence: string;
  verdict: "supported" | "unsupported";
  suggestion?: string | null;
}

export interface StructuredEvidenceItem {
  page?: number;
  text: string;
  source: string;
}

export interface StructuredTrust {
  score: number;
  label: string;
}

export interface StructuredAnswer {
  answer_type: "document_explanation" | "specific_answer" | string;
  document_overview?: string;
  main_idea?: string;
  steps?: string[];
  key_points?: string[];
  main_findings?: string[];
  direct_answer?: string;
  evidence?: StructuredEvidenceItem[];
  trust?: StructuredTrust;
}

export interface SynthesisResponse {
  original_query: string;
  doc_id?: string | null;
  status: SynthesisStatus;
  final_answer: string;
  structured_answer?: StructuredAnswer | null;
  citations: CitationResponse[];
  synthesis_method: string;
  verification_verdict: string;
  verification_method: string;
  hallucination_ratio: number;
  sentence_verdicts: SentenceVerdictResponse[];
  revision_suggestions: string[];
  retry_count: number;
  abstained: boolean;
  abstain_reason?: string | null;
}

export interface IndexResponse {
  documents_indexed: number;
  chunks_indexed: number;
  message: string;
}

export interface DocumentItem {
  id: string;
  doc_id: string;
  filename: string;
  source_type: "file" | "url" | string;
  source_url?: string | null;
  file_type: string;
  status: "processing" | "indexed" | "failed" | string;
  chunk_count: number;
  file_size?: number | null;
  error_message?: string | null;
  created_at: string;
  updated_at: string;
}

export interface DocumentListResponse {
  documents: DocumentItem[];
  total_documents: number;
  total_chunks: number;
}

export interface DocumentUploadResponse {
  success: boolean;
  message: string;
  document: DocumentItem;
}

export interface RetrievalStatsResponse {
  indexed_chunks: number;
  metadata_records: number;
  index_path: string;
}

export interface HealthResponse {
  status: "ok" | "degraded";
  version: string;
  environment: string;
  services: Array<{ name: string; healthy: boolean; detail: string | null }>;
}

/** A single turn in the chat transcript — the frontend's own shape, not the API's. */
export interface ChatTurn {
  id: string;
  query: string;
  status: "pending" | "done" | "error";
  stage?: PipelineStage;
  result?: SynthesisResponse;
  trustReport?: TrustReportResponse;
  errorMessage?: string;
}

export type PipelineStage = "retrieving" | "critiquing" | "scoring" | "synthesizing" | "verifying" | "done";
