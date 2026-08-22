/**
 * Typed API client for the Trust-Aware RAG backend.
 */

import axios, { AxiosError } from "axios";
import type {
  CitationResponse,
  DocumentItem,
  DocumentListResponse,
  DocumentUploadResponse,
  HealthResponse,
  IndexResponse,
  RetrievalStatsResponse,
  SynthesisResponse,
  TrustDashboardResponse,
  TrustReportResponse,
} from "@/types/api";

const BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export class ApiError extends Error {
  constructor(
    public status: number,
    public code: string,
    message: string,
    public details?: unknown
  ) {
    super(message);
    this.name = "ApiError";
  }
}

const client = axios.create({
  baseURL: BASE_URL,
  headers: { "Content-Type": "application/json" },
  timeout: 45000,
});

function normalizeError(error: unknown): ApiError {
  if (axios.isAxiosError(error)) {
    const status = error.response?.status || 500;
    const body = error.response?.data as { code?: string; message?: string; detail?: string } | undefined;
    const code = body?.code || "UPSTREAM_ERROR";
    const message =
      body?.message ||
      (typeof body?.detail === "string" ? body.detail : null) ||
      error.message ||
      "Unknown error occurred.";
    return new ApiError(status, code, message, error.response?.data);
  }
  if (error instanceof Error) {
    return new ApiError(500, "CLIENT_ERROR", error.message);
  }
  return new ApiError(500, "CLIENT_ERROR", "An unexpected error occurred.");
}

async function request<T>(fn: () => Promise<{ data: T }>): Promise<T> {
  try {
    const res = await fn();
    return res.data;
  } catch (error) {
    throw normalizeError(error);
  }
}

export const api = {
  health: (): Promise<HealthResponse> => request(() => client.get("/api/v1/health")),

  /** Runs the full Retriever -> Critic -> Trust chain for a raw question. */
  scoreTrust: (query: string, k = 5, docId?: string): Promise<TrustReportResponse> =>
    request(() => client.post("/api/v1/trust/score", { query, k, doc_id: docId || undefined })),

  /** Runs the full pipeline including Synthesizer + Verifier — what the Chat page calls. */
  runSynthesis: (query: string, k = 5, maxRetries = 2, docId?: string): Promise<SynthesisResponse> =>
    request(() => client.post("/api/v1/agents/synthesis/run", { query, k, max_retries: maxRetries, doc_id: docId || undefined })),

  dashboardStats: (): Promise<TrustDashboardResponse> => request(() => client.get("/api/v1/trust/dashboard")),

  indexDocuments: (directory?: string, chunkSize = 800, chunkOverlap = 100): Promise<IndexResponse> =>
    request(() =>
      client.post("/api/v1/retrieval/index", {
        directory,
        chunk_size: chunkSize,
        chunk_overlap: chunkOverlap,
      })
    ),

  retrievalStats: (): Promise<RetrievalStatsResponse> => request(() => client.get("/api/v1/retrieval/stats")),

  /** Upload a file (PDF, TXT, DOCX, CSV, JSON, XLSX) into the knowledge base */
  uploadDocument: (file: File, chunkSize = 800, chunkOverlap = 100): Promise<DocumentUploadResponse> => {
    const formData = new FormData();
    formData.append("file", file);
    formData.append("chunk_size", chunkSize.toString());
    formData.append("chunk_overlap", chunkOverlap.toString());
    return request(() =>
      client.post("/api/v1/documents/upload", formData, {
        headers: { "Content-Type": "multipart/form-data" },
      })
    );
  },

  /** Ingest and index a webpage URL into the knowledge base */
  ingestUrl: (url: string, chunkSize = 800, chunkOverlap = 100): Promise<DocumentUploadResponse> =>
    request(() =>
      client.post("/api/v1/documents/url", {
        url,
        chunk_size: chunkSize,
        chunk_overlap: chunkOverlap,
      })
    ),

  /** Get the current active document */
  getActiveDocument: (): Promise<DocumentItem | null> => request(() => client.get("/api/v1/documents/active")),

  /** Set active document */
  activateDocument: (docId: string): Promise<DocumentItem> => request(() => client.post(`/api/v1/documents/${docId}/activate`)),

  /** List all indexed knowledge documents */
  listDocuments: (): Promise<DocumentListResponse> => request(() => client.get("/api/v1/documents")),

  /** Delete a document from Supabase and purge its vectors from FAISS */
  deleteDocument: (documentId: string): Promise<{ success: boolean; message: string }> =>
    request(() => client.delete(`/api/v1/documents/${documentId}`)),

  /** Reindex all documents in the database */
  reindexDocuments: (): Promise<{ documents_indexed: number; chunks_indexed: number; message: string }> =>
    request(() => client.post("/api/v1/documents/reindex")),
};
