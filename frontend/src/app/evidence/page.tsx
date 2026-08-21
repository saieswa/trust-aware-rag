"use client";

import { Suspense, useEffect, useState } from "react";
import { useSearchParams } from "next/navigation";
import { Search } from "lucide-react";
import { Button } from "@/components/ui/Button";
import { Skeleton, ErrorAlert } from "@/components/ui/ErrorAlert";
import { EvidenceCard } from "@/components/evidence/EvidenceCard";
import { ContradictionPanel } from "@/components/evidence/ContradictionPanel";
import { TrustGauge } from "@/components/ui/TrustGauge";
import { decisionLabel } from "@/lib/utils";
import { api, ApiError } from "@/lib/api";
import type { TrustReportResponse } from "@/types/api";

function EvidenceViewerContent() {
  const searchParams = useSearchParams();
  const highlightedChunk = searchParams.get("chunk");

  const [query, setQuery] = useState("");
  const [report, setReport] = useState<TrustReportResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const runSearch = async (q: string) => {
    if (!q.trim()) return;
    setLoading(true);
    setError(null);
    try {
      const result = await api.scoreTrust(q);
      setReport(result);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Couldn't load evidence.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (highlightedChunk && report) {
      const el = document.getElementById(`evidence-${highlightedChunk}`);
      el?.scrollIntoView({ behavior: "smooth", block: "center" });
    }
  }, [highlightedChunk, report]);

  return (
    <div className="mx-auto max-w-3xl px-6 py-8">
      <h1 className="font-mono text-sm font-semibold text-ink-primary">Evidence Viewer</h1>
      <p className="text-xs text-ink-muted mt-0.5 mb-5">
        Inspect exactly what evidence a question would draw on, how it was labeled, and any contradictions found.
      </p>

      <form
        onSubmit={(e) => {
          e.preventDefault();
          runSearch(query);
        }}
        className="flex gap-2 mb-6"
      >
        <input
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="Enter a question to inspect its evidence…"
          className="flex-1 rounded-md border border-hairline bg-raised px-3 py-2 text-sm text-ink-primary placeholder:text-ink-muted focus:outline-none focus-visible:ring-2 focus-visible:ring-accent-phosphor"
        />
        <Button type="submit" disabled={loading || !query.trim()}>
          <Search className="h-4 w-4" />
          Inspect
        </Button>
      </form>

      {loading && (
        <div className="flex flex-col gap-3">
          <Skeleton className="h-24 w-full" />
          <Skeleton className="h-24 w-full" />
          <Skeleton className="h-24 w-full" />
        </div>
      )}

      {error && <ErrorAlert message={error} onRetry={() => runSearch(query)} />}

      {!loading && !error && report && (
        <div className="flex flex-col gap-4">
          <div className="flex items-center justify-between rounded-md border border-hairline bg-panel px-5 py-4">
            <div>
              <p className="text-xs uppercase tracking-wide text-ink-muted">Decision</p>
              <p className="font-mono text-sm text-ink-primary mt-0.5">{decisionLabel(report.decision)}</p>
            </div>
            <TrustGauge score={report.trust_score} decision={report.decision} label="trust score" />
          </div>

          <ContradictionPanel contradictions={report.contradictions} />

          <div className="flex flex-col gap-3">
            {report.evidence.map((e) => (
              <EvidenceCard key={e.chunk_id} evidence={e} highlighted={e.chunk_id === highlightedChunk} />
            ))}
            {report.evidence.length === 0 && (
              <p className="text-sm text-ink-muted text-center py-8">No evidence was retrieved for this question.</p>
            )}
          </div>
        </div>
      )}

      {!loading && !error && !report && (
        <p className="text-sm text-ink-muted text-center py-16">
          Enter a question above to see exactly what evidence backs it.
        </p>
      )}
    </div>
  );
}

export default function EvidenceViewerPage() {
  return (
    <Suspense fallback={null}>
      <EvidenceViewerContent />
    </Suspense>
  );
}
