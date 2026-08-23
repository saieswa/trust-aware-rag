"use client";

import React, { useState, useMemo } from "react";
import Link from "next/link";
import {
  RefreshCw,
  Search,
  FileText,
  CheckCircle2,
  AlertTriangle,
  ShieldAlert,
  ShieldCheck,
  Cpu,
  ExternalLink,
  ChevronLeft,
  ChevronRight,
  Filter,
  BarChart3,
  BookOpen,
} from "lucide-react";
import { Button } from "@/components/ui/Button";
import { Badge } from "@/components/ui/Badge";
import { Skeleton, ErrorAlert } from "@/components/ui/ErrorAlert";
import {
  MetricSummaryCard,
  TrustScoreSection,
  DecisionBreakdownWidget,
  EvidenceAnalysisWidget,
} from "@/components/dashboard/DashboardWidgets";
import { useTrustDashboard } from "@/hooks/useTrustDashboard";
import type { EvaluationHistoryItem, Decision } from "@/types/api";

const PAGE_SIZE = 8;

export default function TrustDashboardPage() {
  const { data, loading, error, refresh } = useTrustDashboard();

  // Search & Filter State for Evaluation History
  const [searchTerm, setSearchTerm] = useState("");
  const [selectedDecision, setSelectedDecision] = useState<string>("all");
  const [selectedDoc, setSelectedDoc] = useState<string>("all");
  const [currentPage, setCurrentPage] = useState(1);

  // Derived unique document names from history
  const uniqueDocs = useMemo(() => {
    if (!data?.history) return [];
    const set = new Set<string>();
    data.history.forEach((h) => {
      if (h.document_name) set.add(h.document_name);
    });
    return Array.from(set);
  }, [data?.history]);

  // Filtered History
  const filteredHistory = useMemo(() => {
    if (!data?.history) return [];
    return data.history.filter((item) => {
      const matchSearch =
        item.query.toLowerCase().includes(searchTerm.toLowerCase()) ||
        item.document_name.toLowerCase().includes(searchTerm.toLowerCase());
      const matchDecision =
        selectedDecision === "all" || item.decision === selectedDecision;
      const matchDoc =
        selectedDoc === "all" || item.document_name === selectedDoc;
      return matchSearch && matchDecision && matchDoc;
    });
  }, [data?.history, searchTerm, selectedDecision, selectedDoc]);

  // Pagination calculation
  const totalPages = Math.ceil(filteredHistory.length / PAGE_SIZE) || 1;
  const paginatedHistory = useMemo(() => {
    const start = (currentPage - 1) * PAGE_SIZE;
    return filteredHistory.slice(start, start + PAGE_SIZE);
  }, [filteredHistory, currentPage]);

  const handlePageChange = (page: number) => {
    setCurrentPage(Math.max(1, Math.min(page, totalPages)));
  };

  // Dynamic Overall Interpretation Generator
  const overallSummary = useMemo(() => {
    if (!data || data.total_queries === 0) return null;
    const total = data.total_queries;
    const trustPct = Math.round(data.average_trust_score * 100);
    const trustTier =
      trustPct >= 80 ? "high" : trustPct >= 50 ? "moderate" : "low";
    const supported = data.decision_counts.answer || 0;
    const needsMore = data.decision_counts.retrieve_more || 0;
    const abstained = data.decision_counts.abstain || 0;
    const contradictionPct = Math.round(data.average_contradiction_score * 100);

    const contradictionNarrative =
      contradictionPct === 0
        ? "No contradictions were detected in the evaluated evidence."
        : `An average contradiction rate of ${contradictionPct}% was detected among retrieved evidence passages.`;

    return `${total} question${total === 1 ? "" : "s"} ${total === 1 ? "has" : "have"} been evaluated so far. The average trust score is ${trustPct}%, indicating ${trustTier} evidence support. ${supported} question${supported === 1 ? "" : "s"} received sufficient evidence, ${needsMore} required more evidence, and ${abstained} ${abstained === 1 ? "was" : "were"} abstained from. ${contradictionNarrative}`;
  }, [data]);

  return (
    <div className="mx-auto max-w-5xl px-6 py-8 space-y-8">
      {/* 1. HEADER */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-hairline pb-4">
        <div>
          <h1 className="font-mono text-base font-semibold text-ink-primary">
            Trust-RAG Evaluation Dashboard
          </h1>
          <p className="text-xs text-ink-muted mt-0.5 max-w-2xl">
            Understand how reliably Trust-RAG answers questions using evidence from your uploaded documents.
          </p>
        </div>
        <Button variant="secondary" size="sm" onClick={refresh} disabled={loading}>
          <RefreshCw className={`h-3.5 w-3.5 ${loading ? "animate-spin" : ""}`} />
          Refresh Data
        </Button>
      </div>

      {loading && (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          <Skeleton className="h-28" />
          <Skeleton className="h-28" />
          <Skeleton className="h-28" />
          <Skeleton className="h-44 sm:col-span-2 lg:col-span-3" />
        </div>
      )}

      {error && <ErrorAlert message={error} onRetry={refresh} />}

      {!loading && !error && data && (
        <>
          {data.total_queries === 0 ? (
            <div className="flex flex-col items-center justify-center py-20 text-center rounded-xl border border-hairline bg-panel/40 p-8">
              <BarChart3 className="h-10 w-10 text-accent-phosphor/60 mb-3" />
              <h2 className="font-mono text-sm font-semibold text-ink-primary">
                No evaluation data recorded yet
              </h2>
              <p className="text-xs text-ink-muted max-w-md mt-1 mb-4">
                Ask questions on the <strong>Chat</strong> or <strong>Evidence</strong> page to record historical evaluation metrics from your active documents.
              </p>
              <Link href="/chat">
                <Button size="sm">Go to Chat</Button>
              </Link>
            </div>
          ) : (
            <div className="space-y-8">
              {/* 2. SUMMARY METRIC CARDS (5 Cards Grid) */}
              <div>
                <h2 className="text-xs font-mono font-semibold uppercase tracking-wider text-accent-phosphor mb-3">
                  Summary Metrics
                </h2>
                <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-3.5">
                  {/* Card A: Questions Evaluated */}
                  <MetricSummaryCard
                    title="Questions Evaluated"
                    value={data.total_queries}
                    description="Total number of questions evaluated by Trust-RAG."
                    icon={<FileText className="h-3.5 w-3.5" />}
                  />

                  {/* Card B: Average Trust Score */}
                  <MetricSummaryCard
                    title="Avg. Trust Score"
                    value={`${Math.round(data.average_trust_score * 100)}%`}
                    description="Overall confidence that evaluated answers were supported by available evidence."
                    badge={{
                      label:
                        data.average_trust_score >= 0.8
                          ? "High Trust"
                          : data.average_trust_score >= 0.5
                          ? "Moderate Trust"
                          : "Low Trust",
                      tone:
                        data.average_trust_score >= 0.8
                          ? "green"
                          : data.average_trust_score >= 0.5
                          ? "amber"
                          : "red",
                    }}
                    tooltip="Trust score combines evidence relevance, agreement, citation support, and consistency."
                    icon={<ShieldCheck className="h-3.5 w-3.5" />}
                  />

                  {/* Card C: Supported Answers */}
                  <MetricSummaryCard
                    title="Supported Answers"
                    value={data.decision_counts.answer || 0}
                    description="Questions where the system found sufficient evidence to provide an answer."
                    badge={{
                      label: `${Math.round(((data.decision_counts.answer || 0) / data.total_queries) * 100)}%`,
                      tone: "green",
                    }}
                    icon={<CheckCircle2 className="h-3.5 w-3.5 text-signal-green" />}
                  />

                  {/* Card D: Needs More Evidence */}
                  <MetricSummaryCard
                    title="Needs More Evidence"
                    value={data.decision_counts.retrieve_more || 0}
                    description="Questions where available evidence was not sufficient for a confident answer."
                    badge={{
                      label: `${Math.round(((data.decision_counts.retrieve_more || 0) / data.total_queries) * 100)}%`,
                      tone: "amber",
                    }}
                    icon={<AlertTriangle className="h-3.5 w-3.5 text-amber-400" />}
                  />

                  {/* Card E: Abstained */}
                  <MetricSummaryCard
                    title="Abstained (Safe)"
                    value={data.decision_counts.abstain || 0}
                    description="Questions where the system safely avoided giving an unsupported answer."
                    badge={{
                      label: `${Math.round(((data.decision_counts.abstain || 0) / data.total_queries) * 100)}%`,
                      tone: "neutral",
                    }}
                    tooltip="Abstention is an active safety behavior to prevent hallucination when evidence is absent."
                    icon={<ShieldAlert className="h-3.5 w-3.5 text-accent-phosphor" />}
                  />
                </div>
              </div>

              {/* 3 & 4. TRUST SCORE SECTION & DECISION BREAKDOWN */}
              <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
                <TrustScoreSection score={data.average_trust_score} />
                <DecisionBreakdownWidget counts={data.decision_counts} total={data.total_queries} />
              </div>

              {/* 5 & 8. EVIDENCE ANALYSIS & LLM USAGE */}
              <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
                <div className="lg:col-span-2">
                  <EvidenceAnalysisWidget
                    agreementScore={data.average_agreement_score}
                    contradictionScore={data.average_contradiction_score}
                  />
                </div>

                {/* LLM Usage Widget */}
                <div className="rounded-xl border border-hairline bg-panel/70 p-5 shadow-sm space-y-3 flex flex-col justify-between">
                  <div>
                    <div className="flex items-center gap-2 mb-2">
                      <Cpu className="h-4 w-4 text-accent-phosphor" />
                      <h3 className="text-xs font-mono font-semibold uppercase tracking-wider text-ink-primary">
                        LLM Usage Rate
                      </h3>
                    </div>
                    <div className="flex items-baseline gap-2 mb-2">
                      <span className="font-mono text-3xl font-bold text-ink-primary">
                        {Math.round(data.llm_usage_rate * 100)}%
                      </span>
                    </div>
                    <p className="text-xs text-ink-muted leading-relaxed">
                      Percentage of evaluations that used the LLM-based critique or labeling path.
                    </p>
                  </div>
                  <div className="rounded-lg bg-raised/50 border border-hairline/60 p-2.5 text-[11px] text-ink-muted">
                    {data.llm_usage_rate === 0
                      ? "Evaluations are currently running on deterministic semantic heuristics."
                      : "Evaluations use hybrid LLM fact-checking and semantic heuristics."}
                  </div>
                </div>
              </div>

              {/* 9. OVERALL DYNAMIC INTERPRETATION */}
              {overallSummary && (
                <div className="rounded-xl border border-hairline bg-panel/80 p-5 shadow-sm">
                  <h3 className="text-xs font-mono font-semibold uppercase tracking-wider text-accent-phosphor mb-2">
                    Overall Evaluation Summary
                  </h3>
                  <p className="text-sm leading-relaxed text-ink-primary font-sans">
                    {overallSummary}
                  </p>
                </div>
              )}

              {/* 7. DOCUMENT-WISE PERFORMANCE */}
              {data.document_performance && data.document_performance.length > 0 && (
                <div className="rounded-xl border border-hairline bg-panel/70 p-5 shadow-sm space-y-4">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <BookOpen className="h-4 w-4 text-accent-phosphor" />
                      <h3 className="text-xs font-mono font-semibold uppercase tracking-wider text-ink-primary">
                        Document Performance Breakdown
                      </h3>
                    </div>
                    <span className="text-[11px] font-mono text-ink-muted">
                      {data.document_performance.length} document{data.document_performance.length !== 1 ? "s" : ""} evaluated
                    </span>
                  </div>

                  <div className="overflow-x-auto rounded-lg border border-hairline">
                    <table className="w-full text-left text-xs">
                      <thead className="border-b border-hairline bg-raised font-mono text-[11px] uppercase tracking-wider text-ink-muted">
                        <tr>
                          <th className="px-3.5 py-2.5">Document</th>
                          <th className="px-3 py-2.5 text-center">Evaluated</th>
                          <th className="px-3 py-2.5 text-center">Avg. Trust</th>
                          <th className="px-3 py-2.5 text-center">Answer</th>
                          <th className="px-3 py-2.5 text-center">Needs Evidence</th>
                          <th className="px-3 py-2.5 text-center">Abstained</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-hairline font-sans">
                        {data.document_performance.map((doc) => {
                          const avgPct = Math.round(doc.average_trust_score * 100);
                          return (
                            <tr key={doc.doc_id} className="hover:bg-raised/40 transition-colors">
                              <td className="px-3.5 py-3 font-medium text-ink-primary flex items-center gap-2">
                                <FileText className="h-3.5 w-3.5 text-accent-phosphor shrink-0" />
                                <span className="truncate max-w-[220px]" title={doc.document_name}>
                                  {doc.document_name}
                                </span>
                              </td>
                              <td className="px-3 py-3 text-center font-mono text-ink-primary">
                                {doc.total_queries}
                              </td>
                              <td className="px-3 py-3 text-center font-mono">
                                <Badge
                                  tone={avgPct >= 80 ? "green" : avgPct >= 50 ? "amber" : "red"}
                                  className="text-[10px] px-1.5 py-0"
                                >
                                  {avgPct}%
                                </Badge>
                              </td>
                              <td className="px-3 py-3 text-center font-mono text-signal-green">
                                {doc.supported_count}
                              </td>
                              <td className="px-3 py-3 text-center font-mono text-amber-400">
                                {doc.needs_more_evidence_count}
                              </td>
                              <td className="px-3 py-3 text-center font-mono text-ink-muted">
                                {doc.abstained_count}
                              </td>
                            </tr>
                          );
                        })}
                      </tbody>
                    </table>
                  </div>
                </div>
              )}

              {/* 6. EVALUATION HISTORY TABLE */}
              <div className="rounded-xl border border-hairline bg-panel/70 p-5 shadow-sm space-y-4">
                <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
                  <div>
                    <h3 className="text-xs font-mono font-semibold uppercase tracking-wider text-ink-primary">
                      Evaluation History
                    </h3>
                    <p className="text-[11px] text-ink-muted mt-0.5">
                      Log of evaluated queries, trust decisions, and document associations.
                    </p>
                  </div>

                  {/* Search and Filters */}
                  <div className="flex flex-wrap items-center gap-2">
                    {/* Search input */}
                    <div className="relative">
                      <Search className="absolute left-2.5 top-2.5 h-3.5 w-3.5 text-ink-muted" />
                      <input
                        type="text"
                        value={searchTerm}
                        onChange={(e) => {
                          setSearchTerm(e.target.value);
                          setCurrentPage(1);
                        }}
                        placeholder="Search question or doc…"
                        className="rounded-md border border-hairline bg-raised pl-8 pr-3 py-1.5 text-xs text-ink-primary placeholder:text-ink-muted focus:outline-none focus-visible:ring-1 focus-visible:ring-accent-phosphor w-44"
                      />
                    </div>

                    {/* Decision Filter */}
                    <select
                      value={selectedDecision}
                      onChange={(e) => {
                        setSelectedDecision(e.target.value);
                        setCurrentPage(1);
                      }}
                      className="rounded-md border border-hairline bg-raised px-2.5 py-1.5 text-xs text-ink-primary focus:outline-none"
                    >
                      <option value="all">All Decisions</option>
                      <option value="answer">Answer</option>
                      <option value="retrieve_more">Needs More Evidence</option>
                      <option value="abstain">Abstain</option>
                    </select>

                    {/* Document Filter */}
                    {uniqueDocs.length > 1 && (
                      <select
                        value={selectedDoc}
                        onChange={(e) => {
                          setSelectedDoc(e.target.value);
                          setCurrentPage(1);
                        }}
                        className="rounded-md border border-hairline bg-raised px-2.5 py-1.5 text-xs text-ink-primary focus:outline-none max-w-[140px] truncate"
                      >
                        <option value="all">All Documents</option>
                        {uniqueDocs.map((doc) => (
                          <option key={doc} value={doc}>
                            {doc}
                          </option>
                        ))}
                      </select>
                    )}
                  </div>
                </div>

                {/* Table */}
                <div className="overflow-x-auto rounded-lg border border-hairline">
                  <table className="w-full text-left text-xs">
                    <thead className="border-b border-hairline bg-raised font-mono text-[11px] uppercase tracking-wider text-ink-muted">
                      <tr>
                        <th className="px-3.5 py-2.5">Question</th>
                        <th className="px-3 py-2.5">Document</th>
                        <th className="px-3 py-2.5 text-center">Decision</th>
                        <th className="px-3 py-2.5 text-center">Trust Score</th>
                        <th className="px-3 py-2.5">Date / Time</th>
                        <th className="px-3.5 py-2.5 text-right">Details</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-hairline font-sans">
                      {paginatedHistory.map((item) => {
                        const scorePct = Math.round(item.trust_score * 100);
                        const dateFormatted = item.created_at
                          ? new Date(item.created_at).toLocaleString([], {
                              month: "short",
                              day: "numeric",
                              hour: "2-digit",
                              minute: "2-digit",
                            })
                          : "—";

                        return (
                          <tr key={item.id} className="hover:bg-raised/40 transition-colors">
                            <td className="px-3.5 py-3 font-medium text-ink-primary max-w-xs truncate">
                              &ldquo;{item.query}&rdquo;
                            </td>
                            <td className="px-3 py-3 text-ink-muted font-mono text-[11px] max-w-[160px] truncate">
                              {item.document_name || "Active Document"}
                            </td>
                            <td className="px-3 py-3 text-center">
                              <Badge
                                tone={
                                  item.decision === "answer"
                                    ? "green"
                                    : item.decision === "retrieve_more"
                                    ? "amber"
                                    : "neutral"
                                }
                                className="font-mono text-[10px] px-1.5 py-0 capitalize"
                              >
                                {item.decision === "retrieve_more" ? "Needs Evidence" : item.decision}
                              </Badge>
                            </td>
                            <td className="px-3 py-3 text-center font-mono font-semibold">
                              <span
                                className={
                                  scorePct >= 80
                                    ? "text-signal-green"
                                    : scorePct >= 50
                                    ? "text-amber-400"
                                    : "text-signal-red"
                                }
                              >
                                {scorePct}%
                              </span>
                            </td>
                            <td className="px-3 py-3 text-ink-muted font-mono text-[10px] whitespace-nowrap">
                              {dateFormatted}
                            </td>
                            <td className="px-3.5 py-3 text-right">
                              <Link
                                href={`/evidence?query=${encodeURIComponent(item.query)}`}
                                className="inline-flex items-center gap-1 font-mono text-[11px] text-accent-phosphor hover:underline"
                              >
                                <span>Inspect</span>
                                <ExternalLink className="h-3 w-3" />
                              </Link>
                            </td>
                          </tr>
                        );
                      })}

                      {paginatedHistory.length === 0 && (
                        <tr>
                          <td colSpan={6} className="px-4 py-8 text-center text-ink-muted">
                            No evaluations match your search filter.
                          </td>
                        </tr>
                      )}
                    </tbody>
                  </table>
                </div>

                {/* Pagination Controls */}
                {totalPages > 1 && (
                  <div className="flex items-center justify-between pt-2">
                    <span className="text-xs font-mono text-ink-muted">
                      Showing {(currentPage - 1) * PAGE_SIZE + 1}–
                      {Math.min(currentPage * PAGE_SIZE, filteredHistory.length)} of {filteredHistory.length}
                    </span>
                    <div className="flex items-center gap-1.5">
                      <Button
                        variant="secondary"
                        size="sm"
                        onClick={() => handlePageChange(currentPage - 1)}
                        disabled={currentPage === 1}
                        className="px-2 py-1 h-7"
                      >
                        <ChevronLeft className="h-3.5 w-3.5" />
                      </Button>
                      <span className="text-xs font-mono text-ink-primary px-2">
                        {currentPage} / {totalPages}
                      </span>
                      <Button
                        variant="secondary"
                        size="sm"
                        onClick={() => handlePageChange(currentPage + 1)}
                        disabled={currentPage === totalPages}
                        className="px-2 py-1 h-7"
                      >
                        <ChevronRight className="h-3.5 w-3.5" />
                      </Button>
                    </div>
                  </div>
                )}
              </div>
            </div>
          )}
        </>
      )}
    </div>
  );
}
