"use client";

import { Suspense, useEffect, useState } from "react";
import { useSearchParams } from "next/navigation";
import { Search, FileText, AlertCircle } from "lucide-react";
import { Button } from "@/components/ui/Button";
import { Badge } from "@/components/ui/Badge";
import { Skeleton, ErrorAlert } from "@/components/ui/ErrorAlert";
import { EvidenceCard } from "@/components/evidence/EvidenceCard";
import { ContradictionPanel } from "@/components/evidence/ContradictionPanel";
import { TrustGauge } from "@/components/ui/TrustGauge";
import { ActiveDocumentBadge } from "@/components/common/ActiveDocumentBadge";
import { decisionLabel } from "@/lib/utils";
import { api, ApiError } from "@/lib/api";
import type { DocumentItem, TrustReportResponse } from "@/types/api";

function EvidenceViewerContent() {
  const searchParams = useSearchParams();
  const highlightedChunk = searchParams.get("chunk");

  const [activeDoc, setActiveDoc] = useState<DocumentItem | null>(null);
  const [initialLoading, setInitialLoading] = useState(true);
  const [query, setQuery] = useState("");
  const [report, setReport] = useState<TrustReportResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api
      .getActiveDocument()
      .then((doc) => setActiveDoc(doc))
      .catch(() => setActiveDoc(null))
      .finally(() => setInitialLoading(false));
  }, []);

  const runSearch = async (q: string, docId?: string) => {
    const targetDocId = docId || activeDoc?.doc_id;
    if (!q.trim()) return;

    if (!targetDocId) {
      setReport(null);
      setError("No document indexed. Please upload or activate a document in Admin first.");
      return;
    }

    setLoading(true);
    setError(null);
    try {
      const result = await api.scoreTrust(q, 5, targetDocId);
      // Filter out any chunk that does not belong to targetDocId
      const sanitizedEvidence = (result.evidence || []).filter((e) => e.doc_id === targetDocId);
      setReport({ ...result, evidence: sanitizedEvidence });
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Couldn't load evidence.");
    } finally {
      setLoading(false);
    }
  };

  const handleDocChange = (doc: DocumentItem) => {
    setActiveDoc(doc);
    setReport(null);
    if (query.trim()) {
      runSearch(query, doc.doc_id);
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
      {/* Header with Active Document Indicator */}
      <div className="flex items-center justify-between mb-4">
        <div>
          <h1 className="font-mono text-sm font-semibold text-ink-primary">Evidence Viewer</h1>
          <p className="text-xs text-ink-muted mt-0.5">
            Inspect evidence retrieved strictly from the currently active document.
          </p>
        </div>
        <ActiveDocumentBadge activeDocId={activeDoc?.doc_id} onDocChange={handleDocChange} />
      </div>

      {/* Active Document Status Banner */}
      <div className="mb-6 rounded-lg border border-hairline bg-panel p-4 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <FileText className="h-5 w-5 text-accent-phosphor shrink-0" />
          <div>
            <div className="flex items-center gap-2">
              <span className="text-xs font-semibold text-ink-primary">
                Active document: {activeDoc ? activeDoc.filename : "None"}
              </span>
              {activeDoc && <span className="font-mono text-[10px] text-ink-muted">({activeDoc.doc_id})</span>}
            </div>
            <div className="flex items-center gap-2 mt-0.5 text-xs">
              <span className="text-ink-muted">Status:</span>
              <Badge tone={activeDoc ? "green" : "amber"}>
                {activeDoc ? "Indexed" : "No document indexed"}
              </Badge>
              {activeDoc && (
                <span className="text-[11px] text-ink-muted font-mono ml-2">
                  {activeDoc.chunk_count} chunk(s)
                </span>
              )}
            </div>
          </div>
        </div>
      </div>

      {/* Search Input Form */}
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
          disabled={!activeDoc || loading}
          placeholder={
            activeDoc
              ? `Inspect evidence in "${activeDoc.filename}"…`
              : "No document indexed — select or upload a document in Admin first"
          }
          className="flex-1 rounded-md border border-hairline bg-raised px-3 py-2 text-sm text-ink-primary placeholder:text-ink-muted focus:outline-none focus-visible:ring-2 focus-visible:ring-accent-phosphor disabled:opacity-50"
        />
        <Button type="submit" disabled={!activeDoc || loading || !query.trim()}>
          <Search className="h-4 w-4" />
          Inspect
        </Button>
      </form>

      {/* Empty / No Document Indexed State */}
      {!initialLoading && !activeDoc && (
        <div className="rounded-lg border border-hairline bg-panel/40 p-12 text-center">
          <AlertCircle className="h-8 w-8 text-amber-400 mx-auto mb-2" />
          <p className="font-mono text-sm font-semibold text-ink-primary">No document indexed</p>
          <p className="text-xs text-ink-muted mt-1 max-w-sm mx-auto">
            Please go to the <strong>Admin</strong> page to upload a research paper or activate an existing document.
          </p>
        </div>
      )}

      {loading && (
        <div className="flex flex-col gap-3">
          <Skeleton className="h-24 w-full" />
          <Skeleton className="h-24 w-full" />
          <Skeleton className="h-24 w-full" />
        </div>
      )}

      {error && <ErrorAlert message={error} onRetry={() => runSearch(query)} />}

      {/* Results Display */}
      {activeDoc && !loading && !error && report && (
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
              <div className="rounded-lg border border-hairline bg-panel/50 p-8 text-center">
                <p className="font-mono text-sm text-ink-primary">Insufficient evidence in the selected document.</p>
                <p className="text-xs text-ink-muted mt-1">
                  No verified chunks in &ldquo;{activeDoc.filename}&rdquo; met the relevance criteria.
                </p>
              </div>
            )}
          </div>
        </div>
      )}

      {activeDoc && !loading && !error && !report && (
        <p className="text-sm text-ink-muted text-center py-16">
          Enter a question above to see exactly what evidence backs it in <strong>{activeDoc.filename}</strong>.
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
