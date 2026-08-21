"use client";

import { useEffect, useState } from "react";
import { Database, HeartPulse, RefreshCw } from "lucide-react";
import { Button } from "@/components/ui/Button";
import { Card, CardBody, CardHeader } from "@/components/ui/Card";
import { Badge } from "@/components/ui/Badge";
import { ErrorAlert } from "@/components/ui/ErrorAlert";
import { Spinner } from "@/components/ui/LoadingIndicators";
import { api, ApiError } from "@/lib/api";
import type { HealthResponse, IndexResponse, RetrievalStatsResponse } from "@/types/api";

export default function AdminPage() {
  const [health, setHealth] = useState<HealthResponse | null>(null);
  const [stats, setStats] = useState<RetrievalStatsResponse | null>(null);
  const [directory, setDirectory] = useState("data/sample_documents");
  const [indexing, setIndexing] = useState(false);
  const [indexResult, setIndexResult] = useState<IndexResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  const loadStatus = async () => {
    setError(null);
    try {
      const [healthData, statsData] = await Promise.all([api.health(), api.retrievalStats()]);
      setHealth(healthData);
      setStats(statsData);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Couldn't reach the backend.");
    }
  };

  useEffect(() => {
    loadStatus();
  }, []);

  const runIndex = async () => {
    setIndexing(true);
    setError(null);
    setIndexResult(null);
    try {
      const result = await api.indexDocuments(directory);
      setIndexResult(result);
      await loadStatus();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Indexing failed.");
    } finally {
      setIndexing(false);
    }
  };

  return (
    <div className="mx-auto max-w-3xl px-6 py-8">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="font-mono text-sm font-semibold text-ink-primary">Admin</h1>
          <p className="text-xs text-ink-muted mt-0.5">System status and document indexing.</p>
        </div>
        <Button variant="secondary" size="sm" onClick={loadStatus}>
          <RefreshCw className="h-3.5 w-3.5" />
          Refresh
        </Button>
      </div>

      {error && <ErrorAlert message={error} onRetry={loadStatus} className="mb-4" />}

      <div className="flex flex-col gap-4">
        <Card>
          <CardHeader className="flex items-center gap-2">
            <HeartPulse className="h-4 w-4 text-accent-phosphor" />
            <span className="text-sm font-medium text-ink-primary">System health</span>
          </CardHeader>
          <CardBody>
            {!health ? (
              <p className="text-xs text-ink-muted">Checking…</p>
            ) : (
              <div className="flex flex-col gap-2">
                <div className="flex items-center gap-2">
                  <Badge tone={health.status === "ok" ? "green" : "amber"}>{health.status}</Badge>
                  <span className="text-xs text-ink-muted">
                    v{health.version} · {health.environment}
                  </span>
                </div>
                <div className="flex flex-col gap-1 mt-1">
                  {health.services.map((s) => (
                    <div key={s.name} className="flex items-center justify-between text-xs">
                      <span className="text-ink-primary">{s.name}</span>
                      <Badge tone={s.healthy ? "green" : "red"}>{s.healthy ? "healthy" : "down"}</Badge>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </CardBody>
        </Card>

        <Card>
          <CardHeader className="flex items-center gap-2">
            <Database className="h-4 w-4 text-accent-phosphor" />
            <span className="text-sm font-medium text-ink-primary">Document index</span>
          </CardHeader>
          <CardBody className="flex flex-col gap-3">
            {stats && (
              <div className="flex gap-6 text-xs text-ink-muted">
                <span>
                  <span className="font-mono text-ink-primary">{stats.indexed_chunks}</span> chunks indexed
                </span>
                <span>
                  <span className="font-mono text-ink-primary">{stats.metadata_records}</span> metadata records
                </span>
              </div>
            )}

            <div className="flex gap-2">
              <input
                value={directory}
                onChange={(e) => setDirectory(e.target.value)}
                placeholder="data/sample_documents"
                className="flex-1 rounded-md border border-hairline bg-raised px-3 py-2 text-sm font-mono text-ink-primary placeholder:text-ink-muted focus:outline-none focus-visible:ring-2 focus-visible:ring-accent-phosphor"
              />
              <Button onClick={runIndex} disabled={indexing}>
                {indexing && <Spinner />}
                {indexing ? "Indexing…" : "Re-index"}
              </Button>
            </div>

            {indexResult && (
              <p className="text-xs text-signal-green">
                Indexed {indexResult.documents_indexed} document(s) into {indexResult.chunks_indexed} chunks.
              </p>
            )}
          </CardBody>
        </Card>
      </div>
    </div>
  );
}
