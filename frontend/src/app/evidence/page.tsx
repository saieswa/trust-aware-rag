"use client";

import { Suspense, useEffect, useState } from "react";
import { useSearchParams } from "next/navigation";
import {
  Search,
  FileText,
  AlertCircle,
  CheckCircle2,
  XCircle,
  HelpCircle,
  ChevronDown,
  ChevronUp,
  ShieldCheck,
  Sparkles,
  Info,
} from "lucide-react";
import { Button } from "@/components/ui/Button";
import { Badge } from "@/components/ui/Badge";
import { Card, CardBody, CardHeader } from "@/components/ui/Card";
import { Skeleton, ErrorAlert } from "@/components/ui/ErrorAlert";
import { EvidenceCard } from "@/components/evidence/EvidenceCard";
import { ActiveDocumentBadge } from "@/components/common/ActiveDocumentBadge";
import { api, ApiError } from "@/lib/api";
import type {
  DocumentItem,
  SynthesisResponse,
  TrustReportResponse,
} from "@/types/api";

function EvidenceViewerContent() {
  const searchParams = useSearchParams();
  const initialQuery = searchParams.get("query") || searchParams.get("q") || "";
  const highlightedChunk = searchParams.get("chunk");

  const [activeDoc, setActiveDoc] = useState<DocumentItem | null>(null);
  const [initialLoading, setInitialLoading] = useState(true);
  const [query, setQuery] = useState(initialQuery);
  const [report, setReport] = useState<TrustReportResponse | null>(null);
  const [synthesis, setSynthesis] = useState<SynthesisResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [showAdvanced, setShowAdvanced] = useState(false);

  useEffect(() => {
    api
      .getActiveDocument()
      .then((doc) => {
        setActiveDoc(doc);
        if (doc && initialQuery.trim()) {
          runSearch(initialQuery.trim(), doc.doc_id);
        }
      })
      .catch(() => setActiveDoc(null))
      .finally(() => setInitialLoading(false));
  }, []);

  const runSearch = async (q: string, docId?: string) => {
    const targetDocId = docId || activeDoc?.doc_id;
    if (!q.trim()) return;

    if (!targetDocId) {
      setReport(null);
      setSynthesis(null);
      setError("No document indexed. Please upload or activate a document in Admin first.");
      return;
    }

    setLoading(true);
    setError(null);
    try {
      const [trustRes, synthRes] = await Promise.all([
        api.scoreTrust(q, 5, targetDocId),
        api.runSynthesis(q, 5, 2, targetDocId),
      ]);

      // Strict backend document isolation check: keep only chunks from targetDocId
      const sanitizedEvidence = (trustRes.evidence || []).filter(
        (e) => e.doc_id === targetDocId
      );
      setReport({ ...trustRes, evidence: sanitizedEvidence });
      setSynthesis(synthRes);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Couldn't load evidence.");
    } finally {
      setLoading(false);
    }
  };

  const handleDocChange = (doc: DocumentItem) => {
    setActiveDoc(doc);
    setReport(null);
    setSynthesis(null);
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

  // Confidence Level Derivation
  const getConfidenceBadge = () => {
    if (!report || !synthesis) return null;
    const score = report.trust_score;
    const status = synthesis.status;

    if (status === "verification_failed" || synthesis.hallucination_ratio > 0.2) {
      return {
        label: "Verification Failed",
        tone: "red" as const,
        description: "One or more factual claims could not be verified by document evidence.",
        icon: <XCircle className="h-4 w-4 text-rose-400" />,
        barColor: "bg-rose-500",
      };
    }
    if (status === "abstained" || score < 0.5) {
      return {
        label: "Needs More Evidence",
        tone: "amber" as const,
        description: "Insufficient direct evidence found in the document to answer reliably.",
        icon: <HelpCircle className="h-4 w-4 text-amber-400" />,
        barColor: "bg-amber-500",
      };
    }
    if (score >= 0.75) {
      return {
        label: "High Confidence",
        tone: "green" as const,
        description: "High agreement and direct citation support from the active document.",
        icon: <CheckCircle2 className="h-4 w-4 text-emerald-400" />,
        barColor: "bg-emerald-400",
      };
    }
    return {
      label: "Medium Confidence",
      tone: "amber" as const,
      description: "Answer is supported but evidence specificity or coverage is moderate.",
      icon: <CheckCircle2 className="h-4 w-4 text-amber-400" />,
      barColor: "bg-amber-400",
    };
  };

  const confidence = getConfidenceBadge();
  const topEvidence = report?.evidence ? report.evidence.slice(0, 3) : [];

  return (
    <div className="mx-auto max-w-4xl px-6 py-8">
      {/* Top Header */}
      <div className="flex items-center justify-between mb-4">
        <div>
          <h1 className="font-mono text-sm font-semibold text-ink-primary">Evidence Verification</h1>
          <p className="text-xs text-ink-muted mt-0.5">
            Inspect verified answers and supporting passages from your active document.
          </p>
        </div>
        <ActiveDocumentBadge activeDocId={activeDoc?.doc_id} onDocChange={handleDocChange} />
      </div>

      {/* Active Document Status Banner */}
      <div className="mb-6 rounded-lg border border-hairline bg-panel p-3.5 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <FileText className="h-4 w-4 text-accent-phosphor shrink-0" />
          <div className="flex items-center gap-2">
            <span className="text-xs font-semibold text-ink-primary">
              Active Document: {activeDoc ? activeDoc.filename : "None"}
            </span>
            {activeDoc && (
              <span className="font-mono text-[10px] text-ink-muted">
                ({activeDoc.doc_id} • {activeDoc.chunk_count} chunks)
              </span>
            )}
          </div>
        </div>
        <Badge tone={activeDoc ? "green" : "amber"}>
          {activeDoc ? "Indexed" : "No document indexed"}
        </Badge>
      </div>

      {/* Query Search Bar */}
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
              ? `Ask a question to verify evidence in "${activeDoc.filename}"…`
              : "No document indexed — select or upload a document in Admin first"
          }
          className="flex-1 rounded-md border border-hairline bg-raised px-3.5 py-2.5 text-sm text-ink-primary placeholder:text-ink-muted focus:outline-none focus-visible:ring-2 focus-visible:ring-accent-phosphor disabled:opacity-50"
        />
        <Button type="submit" disabled={!activeDoc || loading || !query.trim()}>
          <Search className="h-4 w-4" />
          Verify
        </Button>
      </form>

      {/* Empty / No Document State */}
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
        <div className="flex flex-col gap-4">
          <Skeleton className="h-32 w-full rounded-lg" />
          <Skeleton className="h-28 w-full rounded-lg" />
          <Skeleton className="h-24 w-full rounded-lg" />
        </div>
      )}

      {error && <ErrorAlert message={error} onRetry={() => runSearch(query)} />}

      {/* Main Results View */}
      {activeDoc && !loading && !error && report && synthesis && (
        <div className="flex flex-col gap-6">
          {/* ============================================================ */}
          {/* SECTION 1: QUESTION & PROMINENT VERIFIED ANSWER */}
          {/* ============================================================ */}
          <Card className="border border-hairline bg-gradient-to-b from-panel to-panel/80 shadow-sm">
            <CardBody className="flex flex-col gap-4 p-5">
              {/* Question Header */}
              <div className="border-b border-hairline pb-3">
                <span className="text-[11px] font-semibold uppercase tracking-wider text-ink-muted">
                  Question
                </span>
                <p className="font-medium text-sm text-ink-primary mt-1">
                  &ldquo;{query}&rdquo;
                </p>
              </div>

              {/* Verified Answer Display */}
              <div>
                <div className="flex items-center justify-between mb-2">
                  <div className="flex items-center gap-2">
                    <Sparkles className="h-4 w-4 text-accent-phosphor" />
                    <span className="text-xs font-semibold uppercase tracking-wider text-ink-primary">
                      Verified Answer
                    </span>
                  </div>
                  {confidence && (
                    <Badge tone={confidence.tone}>
                      {confidence.label}
                    </Badge>
                  )}
                </div>

                <div className="rounded-md bg-raised/70 border border-hairline/80 p-4">
                  <p className="text-sm leading-relaxed text-ink-primary font-normal">
                    {synthesis.final_answer}
                  </p>
                </div>
              </div>

              {/* Confidence Score Bar */}
              {confidence && (
                <div className="flex items-center justify-between rounded-md bg-panel border border-hairline px-4 py-2.5">
                  <div className="flex items-center gap-2">
                    {confidence.icon}
                    <span className="text-xs font-medium text-ink-primary">
                      {confidence.label}
                    </span>
                    <span className="text-xs text-ink-muted font-mono ml-1">
                      (Trust Score: {Math.round(report.trust_score * 100)}%)
                    </span>
                  </div>
                  <div className="w-28 h-2 rounded-full bg-raised overflow-hidden border border-hairline">
                    <div
                      className={`h-full rounded-full transition-all duration-500 ${confidence.barColor}`}
                      style={{ width: `${Math.round(report.trust_score * 100)}%` }}
                    />
                  </div>
                </div>
              )}
            </CardBody>
          </Card>

          {/* ============================================================ */}
          {/* SECTION 2: WHY IS THIS ANSWER TRUSTED? */}
          {/* ============================================================ */}
          <div className="rounded-lg border border-hairline bg-panel p-4">
            <div className="flex items-center gap-2 mb-3">
              <ShieldCheck className="h-4 w-4 text-accent-phosphor" />
              <h2 className="text-xs font-semibold uppercase tracking-wider text-ink-primary">
                Why is this answer trusted?
              </h2>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-2.5 text-xs">
              {/* Point 1: Direct Support */}
              <div className="flex items-start gap-2 rounded bg-raised/50 border border-hairline/50 p-2.5">
                {report.diagnostics.support_count > 0 ? (
                  <CheckCircle2 className="h-4 w-4 text-emerald-400 shrink-0 mt-0.5" />
                ) : (
                  <HelpCircle className="h-4 w-4 text-amber-400 shrink-0 mt-0.5" />
                )}
                <div>
                  <span className="font-semibold text-ink-primary">Direct Evidence Support</span>
                  <p className="text-ink-muted text-[11px] mt-0.5">
                    {report.diagnostics.support_count > 0
                      ? `${report.diagnostics.support_count} retrieved passage(s) directly verify the answer claims.`
                      : "Evidence provides limited or neutral direct verification."}
                  </p>
                </div>
              </div>

              {/* Point 2: Active Document Provenance */}
              <div className="flex items-start gap-2 rounded bg-raised/50 border border-hairline/50 p-2.5">
                <CheckCircle2 className="h-4 w-4 text-emerald-400 shrink-0 mt-0.5" />
                <div>
                  <span className="font-semibold text-ink-primary">Document Isolation</span>
                  <p className="text-ink-muted text-[11px] mt-0.5 truncate max-w-[260px]">
                    100% of evidence belongs strictly to <strong>{activeDoc.filename}</strong>.
                  </p>
                </div>
              </div>

              {/* Point 3: Contradiction Check */}
              <div className="flex items-start gap-2 rounded bg-raised/50 border border-hairline/50 p-2.5">
                {report.diagnostics.contradiction_count === 0 ? (
                  <CheckCircle2 className="h-4 w-4 text-emerald-400 shrink-0 mt-0.5" />
                ) : (
                  <XCircle className="h-4 w-4 text-rose-400 shrink-0 mt-0.5" />
                )}
                <div>
                  <span className="font-semibold text-ink-primary">Consistency Check</span>
                  <p className="text-ink-muted text-[11px] mt-0.5">
                    {report.diagnostics.contradiction_count === 0
                      ? "Zero conflicting or contradictory statements detected."
                      : `${report.diagnostics.contradiction_count} potential contradiction(s) flagged.`}
                  </p>
                </div>
              </div>

              {/* Point 4: Sentence Verification */}
              <div className="flex items-start gap-2 rounded bg-raised/50 border border-hairline/50 p-2.5">
                {synthesis.hallucination_ratio === 0 ? (
                  <CheckCircle2 className="h-4 w-4 text-emerald-400 shrink-0 mt-0.5" />
                ) : (
                  <AlertCircle className="h-4 w-4 text-amber-400 shrink-0 mt-0.5" />
                )}
                <div>
                  <span className="font-semibold text-ink-primary">Fact Verification</span>
                  <p className="text-ink-muted text-[11px] mt-0.5">
                    {synthesis.hallucination_ratio === 0
                      ? "Passed sentence-level verification (0% hallucination ratio)."
                      : `Flagged ${(synthesis.hallucination_ratio * 100).toFixed(0)}% unsupported claims.`}
                  </p>
                </div>
              </div>
            </div>
          </div>

          {/* ============================================================ */}
          {/* SECTION 3: TOP SUPPORTING EVIDENCE CHUNKS */}
          {/* ============================================================ */}
          <div className="flex flex-col gap-3">
            <div className="flex items-center justify-between">
              <h2 className="text-xs font-semibold uppercase tracking-wider text-ink-primary">
                Top Supporting Evidence ({topEvidence.length})
              </h2>
              <span className="text-[11px] text-ink-muted">
                Showing top passages ranked by relevance &amp; quality
              </span>
            </div>

            {topEvidence.map((e, idx) => (
              <EvidenceCard
                key={e.chunk_id}
                evidence={e}
                index={idx}
                highlighted={e.chunk_id === highlightedChunk}
              />
            ))}

            {topEvidence.length === 0 && (
              <div className="rounded-lg border border-hairline bg-panel/50 p-8 text-center">
                <p className="font-mono text-sm text-ink-primary">
                  Insufficient evidence in the selected document.
                </p>
                <p className="text-xs text-ink-muted mt-1">
                  No verified chunks in &ldquo;{activeDoc.filename}&rdquo; met the relevance criteria.
                </p>
              </div>
            )}
          </div>

          {/* ============================================================ */}
          {/* SECTION 4: ADVANCED TECHNICAL DETAILS (COLLAPSIBLE) */}
          {/* ============================================================ */}
          <div className="rounded-lg border border-hairline bg-panel/60 overflow-hidden">
            <button
              type="button"
              onClick={() => setShowAdvanced(!showAdvanced)}
              className="flex items-center justify-between w-full px-4 py-3 text-xs font-medium text-ink-muted hover:text-ink-primary hover:bg-raised/40 transition-colors"
            >
              <div className="flex items-center gap-2">
                <Info className="h-3.5 w-3.5 text-accent-phosphor" />
                <span>Advanced Technical Details &amp; Diagnostics</span>
              </div>
              {showAdvanced ? (
                <ChevronUp className="h-3.5 w-3.5" />
              ) : (
                <ChevronDown className="h-3.5 w-3.5" />
              )}
            </button>

            {showAdvanced && (
              <div className="border-t border-hairline p-4 flex flex-col gap-3 text-xs bg-raised/30">
                <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
                  <div className="rounded border border-hairline bg-panel p-2.5">
                    <span className="text-[10px] text-ink-muted uppercase">Target Doc ID</span>
                    <p className="font-mono text-xs text-accent-phosphor truncate mt-0.5">
                      {activeDoc.doc_id}
                    </p>
                  </div>
                  <div className="rounded border border-hairline bg-panel p-2.5">
                    <span className="text-[10px] text-ink-muted uppercase">Labeling Method</span>
                    <p className="font-mono text-xs text-ink-primary mt-0.5">
                      {report.labeling_method}
                    </p>
                  </div>
                  <div className="rounded border border-hairline bg-panel p-2.5">
                    <span className="text-[10px] text-ink-muted uppercase">Contradiction Method</span>
                    <p className="font-mono text-xs text-ink-primary mt-0.5">
                      {report.contradiction_method}
                    </p>
                  </div>
                  <div className="rounded border border-hairline bg-panel p-2.5">
                    <span className="text-[10px] text-ink-muted uppercase">Hallucination Ratio</span>
                    <p className="font-mono text-xs text-signal-green mt-0.5">
                      {(synthesis.hallucination_ratio * 100).toFixed(1)}%
                    </p>
                  </div>
                </div>

                {/* Raw Feature Breakdown Table */}
                <div className="overflow-x-auto rounded border border-hairline bg-panel mt-1">
                  <table className="w-full text-left text-[11px]">
                    <thead className="border-b border-hairline bg-raised font-mono text-[10px] uppercase tracking-wider text-ink-muted">
                      <tr>
                        <th className="px-3 py-1.5">Feature Metric</th>
                        <th className="px-3 py-1.5">Value</th>
                        <th className="px-3 py-1.5">Weight</th>
                        <th className="px-3 py-1.5 text-right">Contribution</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-hairline font-mono">
                      {Object.entries(report.feature_breakdown || {}).map(([key, f]) => (
                        <tr key={key}>
                          <td className="px-3 py-1.5 text-ink-primary capitalize">
                            {key.replace(/_/g, " ")}
                          </td>
                          <td className="px-3 py-1.5 text-ink-muted">{f.value.toFixed(3)}</td>
                          <td className="px-3 py-1.5 text-ink-muted">{f.weight.toFixed(2)}</td>
                          <td className="px-3 py-1.5 text-right text-accent-phosphor">
                            {f.contribution.toFixed(3)}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            )}
          </div>
        </div>
      )}

      {/* Initial Empty State */}
      {activeDoc && !loading && !error && !report && (
        <p className="text-sm text-ink-muted text-center py-16">
          Enter a question above to verify supporting evidence and trust diagnostics in <strong>{activeDoc.filename}</strong>.
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
