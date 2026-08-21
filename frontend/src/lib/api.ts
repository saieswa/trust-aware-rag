import axios, { AxiosError } from "axios";
import type {
  HealthResponse,
  IndexResponse,
  RetrievalStatsResponse,
  SynthesisResponse,
  TrustDashboardResponse,
  TrustReportResponse,
} from "@/types/api";

/**
 * Single axios instance for every backend call. Base URL comes from the
 * env var set in next.config.js (NEXT_PUBLIC_API_URL), so the same build
 * works against localhost in dev and the deployed backend in production
 * without a code change.
 */
const client = axios.create({
  baseURL: process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000",
  timeout: 60_000, // agent pipelines can take a while — generous timeout
  headers: { "Content-Type": "application/json" },
});

/**
 * Every backend error follows one shape (see ErrorResponse in
 * backend/app/schemas/common.py): { error_code, message, details }. This
 * normalizes any axios failure — network error, timeout, or a structured
 * backend error — into one predictable Error the UI can display directly.
 */
export class ApiError extends Error {
  errorCode: string;
  details?: unknown;

  constructor(message: string, errorCode = "unknown_error", details?: unknown) {
    super(message);
    this.errorCode = errorCode;
    this.details = details;
  }
}

function normalizeError(error: unknown): ApiError {
  if (axios.isAxiosError(error)) {
    const axiosError = error as AxiosError<{ error_code?: string; message?: string }>;
    if (axiosError.response?.data) {
      const { error_code, message } = axiosError.response.data;
      return new ApiError(message || axiosError.message, error_code || "http_error", axiosError.response.data);
    }
    if (axiosError.code === "ECONNABORTED") {
      return new ApiError("The request took too long to respond. Please try again.", "timeout");
    }
    return new ApiError(
      "Couldn't reach the API. Check that the backend is running and reachable.",
      "network_error"
    );
  }
  return new ApiError("Something unexpected went wrong.", "unknown_error");
}

async function request<T>(fn: () => Promise<{ data: T }>): Promise<T> {
  try {
    const response = await fn();
    return response.data;
  } catch (error) {
    throw normalizeError(error);
  }
}

export const api = {
  health: (): Promise<HealthResponse> => request(() => client.get("/api/v1/health")),

  /** Runs the full Retriever -> Critic -> Trust chain for a raw question. */
  scoreTrust: (query: string, k = 5): Promise<TrustReportResponse> =>
    request(() => client.post("/api/v1/trust/score", { query, k })),

  /** Runs the full pipeline including Synthesizer + Verifier — what the Chat page calls. */
  runSynthesis: (query: string, k = 5, maxRetries = 2): Promise<SynthesisResponse> =>
    request(() => client.post("/api/v1/agents/synthesis/run", { query, k, max_retries: maxRetries })),

  dashboardStats: (): Promise<TrustDashboardResponse> => request(() => client.get("/api/v1/trust/dashboard")),

  indexDocuments: (directory?: string, chunkSize = 500, chunkOverlap = 50): Promise<IndexResponse> =>
    request(() =>
      client.post("/api/v1/retrieval/index", {
        directory,
        chunk_size: chunkSize,
        chunk_overlap: chunkOverlap,
      })
    ),

  retrievalStats: (): Promise<RetrievalStatsResponse> => request(() => client.get("/api/v1/retrieval/stats")),
};
