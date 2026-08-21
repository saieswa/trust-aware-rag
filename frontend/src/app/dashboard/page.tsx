"use client";

import { RefreshCw } from "lucide-react";
import { Button } from "@/components/ui/Button";
import { Skeleton, ErrorAlert } from "@/components/ui/ErrorAlert";
import { StatCard, DecisionBreakdown } from "@/components/dashboard/DashboardWidgets";
import { TrustGauge } from "@/components/ui/TrustGauge";
import { formatPercent } from "@/lib/utils";
import { useTrustDashboard } from "@/hooks/useTrustDashboard";

export default function TrustDashboardPage() {
  const { data, loading, error, refresh } = useTrustDashboard();

  return (
    <div className="mx-auto max-w-4xl px-6 py-8">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="font-mono text-sm font-semibold text-ink-primary">Trust Dashboard</h1>
          <p className="text-xs text-ink-muted mt-0.5">Aggregated across every trust score computed so far.</p>
        </div>
        <Button variant="secondary" size="sm" onClick={refresh} disabled={loading}>
          <RefreshCw className={`h-3.5 w-3.5 ${loading ? "animate-spin" : ""}`} />
          Refresh
        </Button>
      </div>

      {loading && (
        <div className="grid gap-4 sm:grid-cols-2">
          <Skeleton className="h-32" />
          <Skeleton className="h-32" />
          <Skeleton className="h-32 sm:col-span-2" />
        </div>
      )}

      {error && <ErrorAlert message={error} onRetry={refresh} />}

      {!loading && !error && data && (
        <>
          {data.total_queries === 0 ? (
            <EmptyDashboard />
          ) : (
            <div className="flex flex-col gap-4">
              <div className="flex flex-col items-center gap-2 rounded-md border border-hairline bg-panel px-5 py-8">
                <TrustGauge score={data.average_trust_score} size="large" label="average trust score" />
                <p className="text-xs text-ink-muted">across {data.total_queries} queries evaluated</p>
              </div>

              <div className="grid gap-4 sm:grid-cols-3">
                <StatCard label="Queries evaluated" value={String(data.total_queries)} />
                <StatCard label="Avg. agreement" value={formatPercent(data.average_agreement_score)} sublabel="evidence labeled 'support'" />
                <StatCard label="Avg. contradiction" value={formatPercent(data.average_contradiction_score)} sublabel="pairs relative to evidence" />
              </div>

              <DecisionBreakdown counts={data.decision_counts} />

              <div className="rounded-md border border-hairline bg-panel px-5 py-4">
                <p className="text-xs uppercase tracking-wide text-ink-muted mb-1">LLM usage rate</p>
                <p className="text-sm text-ink-primary">
                  {formatPercent(data.llm_usage_rate)} of queries used the LLM path for critique/labeling — the rest
                  fell back to the deterministic heuristics.
                </p>
              </div>
            </div>
          )}
        </>
      )}
    </div>
  );
}

function EmptyDashboard() {
  return (
    <div className="flex flex-col items-center gap-2 py-16 text-center">
      <p className="font-mono text-sm text-ink-primary">No queries evaluated yet</p>
      <p className="text-xs text-ink-muted max-w-sm">
        Ask something in Chat or Evidence Viewer — every trust score computed gets logged here.
      </p>
    </div>
  );
}
