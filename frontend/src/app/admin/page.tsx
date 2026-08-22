"use client";

import { useEffect, useRef, useState } from "react";
import {
  AlertCircle,
  CheckCircle2,
  Database,
  FileSpreadsheet,
  FileText,
  Globe,
  HeartPulse,
  Plus,
  RefreshCw,
  Trash2,
  Upload,
  X,
} from "lucide-react";
import { Button } from "@/components/ui/Button";
import { Card, CardBody, CardHeader } from "@/components/ui/Card";
import { Badge } from "@/components/ui/Badge";
import { ErrorAlert } from "@/components/ui/ErrorAlert";
import { Spinner } from "@/components/ui/LoadingIndicators";
import { api, ApiError } from "@/lib/api";
import type {
  DocumentItem,
  DocumentListResponse,
  HealthResponse,
  IndexResponse,
  RetrievalStatsResponse,
} from "@/types/api";

const SUPPORTED_EXTS = [".pdf", ".txt", ".md", ".docx", ".doc", ".csv", ".json", ".xlsx"];

function formatBytes(bytes?: number | null): string {
  if (!bytes || bytes === 0) return "0 B";
  const k = 1024;
  const sizes = ["B", "KB", "MB", "GB"];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return `${parseFloat((bytes / Math.pow(k, i)).toFixed(1))} ${sizes[i]}`;
}

function getFileTypeIcon(fileType: string) {
  const t = fileType.toLowerCase();
  if (t === "pdf" || t === "docx" || t === "doc" || t === "txt" || t === "md") {
    return <FileText className="h-4 w-4 text-accent-phosphor" />;
  }
  if (t === "csv" || t === "xlsx" || t === "json") {
    return <FileSpreadsheet className="h-4 w-4 text-signal-green" />;
  }
  return <Globe className="h-4 w-4 text-accent-phosphor" />;
}

export default function AdminPage() {
  const [health, setHealth] = useState<HealthResponse | null>(null);
  const [stats, setStats] = useState<RetrievalStatsResponse | null>(null);
  const [docList, setDocList] = useState<DocumentListResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);

  // File Upload State
  const [selectedFiles, setSelectedFiles] = useState<File[]>([]);
  const [uploading, setUploading] = useState(false);
  const [isDragging, setIsDragging] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  // URL Ingest State
  const [urlInput, setUrlInput] = useState("");
  const [ingestingUrl, setIngestingUrl] = useState(false);

  // Directory reindex fallback
  const [directory, setDirectory] = useState("data/sample_documents");
  const [indexingDir, setIndexingDir] = useState(false);
  const [indexResult, setIndexResult] = useState<IndexResponse | null>(null);

  // Deleting document state
  const [deletingId, setDeletingId] = useState<string | null>(null);
  const [reindexingAll, setReindexingAll] = useState(false);

  const loadAll = async () => {
    setError(null);
    setLoading(true);
    try {
      const [healthData, statsData, documentsData] = await Promise.all([
        api.health().catch(() => null),
        api.retrievalStats().catch(() => null),
        api.listDocuments().catch(() => null),
      ]);
      if (healthData) setHealth(healthData);
      if (statsData) setStats(statsData);
      if (documentsData) setDocList(documentsData);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Couldn't load admin data.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadAll();
  }, []);

  // ------------------------------------------------------------------ //
  // File Upload Handlers
  // ------------------------------------------------------------------ //

  const handleFileSelect = (files: FileList | null) => {
    if (!files) return;
    const newFiles = Array.from(files);
    setSelectedFiles((prev) => [...prev, ...newFiles]);
  };

  const handleRemoveFile = (index: number) => {
    setSelectedFiles((prev) => prev.filter((_, i) => i !== index));
  };

  const handleUploadFiles = async () => {
    if (selectedFiles.length === 0) return;
    setUploading(true);
    setError(null);
    setSuccessMessage(null);

    let successCount = 0;
    const errors: string[] = [];

    for (const file of selectedFiles) {
      try {
        await api.uploadDocument(file);
        successCount++;
      } catch (err) {
        errors.push(`${file.name}: ${err instanceof ApiError ? err.message : "Upload failed"}`);
      }
    }

    setUploading(false);
    setSelectedFiles([]);

    if (successCount > 0) {
      setSuccessMessage(`Successfully uploaded and indexed ${successCount} document(s).`);
    }
    if (errors.length > 0) {
      setError(`Some files failed: ${errors.join("; ")}`);
    }

    await loadAll();
  };

  // ------------------------------------------------------------------ //
  // URL Ingest Handler
  // ------------------------------------------------------------------ //

  const handleIngestUrl = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!urlInput.trim()) return;

    setIngestingUrl(true);
    setError(null);
    setSuccessMessage(null);

    try {
      const res = await api.ingestUrl(urlInput.trim());
      setSuccessMessage(`Successfully fetched and indexed ${res.document.filename} (${res.document.chunk_count} chunks).`);
      setUrlInput("");
      await loadAll();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to ingest URL.");
    } finally {
      setIngestingUrl(false);
    }
  };

  // ------------------------------------------------------------------ //
  // Delete Document Handler
  // ------------------------------------------------------------------ //

  const handleDeleteDocument = async (docId: string, filename: string) => {
    if (!confirm(`Are you sure you want to delete '${filename}' and purge its vectors?`)) {
      return;
    }
    setDeletingId(docId);
    setError(null);
    setSuccessMessage(null);

    try {
      await api.deleteDocument(docId);
      setSuccessMessage(`Document '${filename}' deleted successfully.`);
      await loadAll();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to delete document.");
    } finally {
      setDeletingId(null);
    }
  };

  // ------------------------------------------------------------------ //
  // Reindex All Handler
  // ------------------------------------------------------------------ //

  const handleReindexAll = async () => {
    setReindexingAll(true);
    setError(null);
    setSuccessMessage(null);

    try {
      const result = await api.reindexDocuments();
      setSuccessMessage(`Reindexing complete: ${result.documents_indexed} document(s), ${result.chunks_indexed} chunk(s).`);
      await loadAll();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Reindexing failed.");
    } finally {
      setReindexingAll(false);
    }
  };

  // ------------------------------------------------------------------ //
  // Directory Reindex Handler
  // ------------------------------------------------------------------ //

  const runIndexDirectory = async () => {
    setIndexingDir(true);
    setError(null);
    setIndexResult(null);
    try {
      const result = await api.indexDocuments(directory);
      setIndexResult(result);
      await loadAll();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Directory indexing failed.");
    } finally {
      setIndexingDir(false);
    }
  };

  return (
    <div className="mx-auto max-w-4xl px-6 py-8">
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="font-mono text-sm font-semibold text-ink-primary">Admin & Knowledge Base</h1>
          <p className="text-xs text-ink-muted mt-0.5">
            Add knowledge sources, manage indexed documents, and monitor cloud database health.
          </p>
        </div>
        <Button variant="secondary" size="sm" onClick={loadAll} disabled={loading}>
          <RefreshCw className={`h-3.5 w-3.5 ${loading ? "animate-spin" : ""}`} />
          Refresh
        </Button>
      </div>

      {/* Notifications */}
      {error && <ErrorAlert message={error} onRetry={loadAll} className="mb-4" />}
      {successMessage && (
        <div className="mb-4 flex items-center justify-between rounded-md border border-signal-green/30 bg-signal-green/10 px-4 py-3 text-xs text-signal-green">
          <div className="flex items-center gap-2">
            <CheckCircle2 className="h-4 w-4 shrink-0" />
            <span>{successMessage}</span>
          </div>
          <button onClick={() => setSuccessMessage(null)} className="text-signal-green/70 hover:text-signal-green">
            <X className="h-4 w-4" />
          </button>
        </div>
      )}

      <div className="flex flex-col gap-6">
        {/* ============================================================ */}
        {/* SECTION 1: ADD KNOWLEDGE (FILES & URLS) */}
        {/* ============================================================ */}
        <Card>
          <CardHeader className="flex items-center gap-2">
            <Plus className="h-4 w-4 text-accent-phosphor" />
            <span className="text-sm font-medium text-ink-primary">Add Knowledge</span>
          </CardHeader>
          <CardBody className="flex flex-col gap-6">
            {/* File Upload Area */}
            <div>
              <label className="text-xs font-semibold text-ink-primary mb-1.5 block">
                Upload Documents (PDF, TXT, DOCX, CSV, JSON, XLSX)
              </label>

              {/* Drag & Drop Zone */}
              <div
                onDragOver={(e) => {
                  e.preventDefault();
                  setIsDragging(true);
                }}
                onDragLeave={() => setIsDragging(false)}
                onDrop={(e) => {
                  e.preventDefault();
                  setIsDragging(false);
                  handleFileSelect(e.dataTransfer.files);
                }}
                onClick={() => fileInputRef.current?.click()}
                className={`flex flex-col items-center justify-center rounded-lg border-2 border-dashed px-6 py-8 text-center transition-colors cursor-pointer ${
                  isDragging
                    ? "border-accent-phosphor bg-accent-phosphor/5"
                    : "border-hairline bg-raised hover:border-ink-muted/50"
                }`}
              >
                <input
                  ref={fileInputRef}
                  type="file"
                  multiple
                  accept={SUPPORTED_EXTS.join(",")}
                  className="hidden"
                  onChange={(e) => handleFileSelect(e.target.files)}
                />
                <Upload className="h-8 w-8 text-ink-muted mb-2" />
                <p className="text-xs font-medium text-ink-primary">
                  Drag &amp; drop files here, or <span className="text-accent-phosphor underline">browse</span>
                </p>
                <p className="text-[11px] text-ink-muted mt-1">
                  Supported formats: PDF, TXT, DOCX, CSV, JSON, XLSX (Max 25MB)
                </p>
              </div>

              {/* Selected Files Preview List */}
              {selectedFiles.length > 0 && (
                <div className="mt-3 flex flex-col gap-2">
                  <span className="text-xs font-medium text-ink-muted">
                    Selected ({selectedFiles.length} file{selectedFiles.length > 1 ? "s" : ""}):
                  </span>
                  <div className="flex flex-col gap-1.5 max-h-48 overflow-y-auto">
                    {selectedFiles.map((file, idx) => (
                      <div
                        key={`${file.name}-${idx}`}
                        className="flex items-center justify-between rounded border border-hairline bg-panel px-3 py-2 text-xs"
                      >
                        <div className="flex items-center gap-2 overflow-hidden">
                          {getFileTypeIcon(file.name.split(".").pop() || "txt")}
                          <span className="truncate text-ink-primary font-medium">{file.name}</span>
                          <Badge tone="neutral">{file.name.split(".").pop()?.toUpperCase()}</Badge>
                          <span className="text-ink-muted">({formatBytes(file.size)})</span>
                        </div>
                        <button
                          onClick={(e) => {
                            e.stopPropagation();
                            handleRemoveFile(idx);
                          }}
                          className="text-ink-muted hover:text-signal-red transition-colors p-1"
                        >
                          <X className="h-3.5 w-3.5" />
                        </button>
                      </div>
                    ))}
                  </div>

                  <div className="mt-2 flex justify-end">
                    <Button onClick={handleUploadFiles} disabled={uploading}>
                      {uploading ? <Spinner /> : <Upload className="h-3.5 w-3.5" />}
                      {uploading ? "Processing & Indexing…" : `Upload & Index (${selectedFiles.length})`}
                    </Button>
                  </div>
                </div>
              )}
            </div>

            <div className="border-t border-hairline pt-4">
              {/* Web URL Ingestion */}
              <label className="text-xs font-semibold text-ink-primary mb-1.5 block">
                Add Website / Webpage Link
              </label>
              <form onSubmit={handleIngestUrl} className="flex gap-2">
                <div className="relative flex-1">
                  <Globe className="absolute left-3 top-2.5 h-4 w-4 text-ink-muted" />
                  <input
                    type="url"
                    value={urlInput}
                    onChange={(e) => setUrlInput(e.target.value)}
                    placeholder="https://example.com/documentation"
                    disabled={ingestingUrl}
                    className="w-full rounded-md border border-hairline bg-raised pl-9 pr-3 py-2 text-sm text-ink-primary placeholder:text-ink-muted focus:outline-none focus-visible:ring-2 focus-visible:ring-accent-phosphor"
                  />
                </div>
                <Button type="submit" disabled={ingestingUrl || !urlInput.trim()}>
                  {ingestingUrl ? <Spinner /> : <Plus className="h-3.5 w-3.5" />}
                  {ingestingUrl ? "Fetching…" : "Add URL & Index"}
                </Button>
              </form>
            </div>
          </CardBody>
        </Card>

        {/* ============================================================ */}
        {/* SECTION 2: DOCUMENT INDEX & KNOWLEDGE MANAGEMENT */}
        {/* ============================================================ */}
        <Card>
          <CardHeader className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Database className="h-4 w-4 text-accent-phosphor" />
              <span className="text-sm font-medium text-ink-primary">Knowledge Sources &amp; Index</span>
            </div>
            <div className="flex items-center gap-2">
              <Button
                variant="secondary"
                size="sm"
                onClick={handleReindexAll}
                disabled={reindexingAll || !docList?.documents.length}
              >
                <RefreshCw className={`h-3 w-3 ${reindexingAll ? "animate-spin" : ""}`} />
                {reindexingAll ? "Reindexing…" : "Reindex All"}
              </Button>
            </div>
          </CardHeader>
          <CardBody className="flex flex-col gap-4">
            {/* Quick Stats */}
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
              <div className="rounded border border-hairline bg-raised p-3">
                <p className="text-[11px] text-ink-muted uppercase">Total Documents</p>
                <p className="font-mono text-lg font-semibold text-ink-primary mt-0.5">
                  {docList?.total_documents ?? 0}
                </p>
              </div>
              <div className="rounded border border-hairline bg-raised p-3">
                <p className="text-[11px] text-ink-muted uppercase">Total Chunks</p>
                <p className="font-mono text-lg font-semibold text-ink-primary mt-0.5">
                  {docList?.total_chunks ?? stats?.indexed_chunks ?? 0}
                </p>
              </div>
              <div className="rounded border border-hairline bg-raised p-3">
                <p className="text-[11px] text-ink-muted uppercase">FAISS Vectors</p>
                <p className="font-mono text-lg font-semibold text-accent-phosphor mt-0.5">
                  {stats?.indexed_chunks ?? 0}
                </p>
              </div>
              <div className="rounded border border-hairline bg-raised p-3">
                <p className="text-[11px] text-ink-muted uppercase">Metadata Records</p>
                <p className="font-mono text-lg font-semibold text-signal-green mt-0.5">
                  {stats?.metadata_records ?? 0}
                </p>
              </div>
            </div>

            {/* Document Table / List */}
            {!docList || docList.documents.length === 0 ? (
              <div className="rounded-md border border-hairline bg-panel p-8 text-center">
                <p className="text-xs font-mono text-ink-primary">No documents indexed yet.</p>
                <p className="text-xs text-ink-muted mt-1">
                  Upload a PDF, TXT, DOCX, CSV, JSON, or paste a URL above to populate your knowledge base.
                </p>
              </div>
            ) : (
              <div className="overflow-x-auto rounded-md border border-hairline">
                <table className="w-full text-left text-xs">
                  <thead className="border-b border-hairline bg-raised font-mono text-[11px] uppercase tracking-wider text-ink-muted">
                    <tr>
                      <th className="px-4 py-2.5">Document / Source</th>
                      <th className="px-3 py-2.5">Type</th>
                      <th className="px-3 py-2.5">Status</th>
                      <th className="px-3 py-2.5">Chunks</th>
                      <th className="px-3 py-2.5">Size</th>
                      <th className="px-3 py-2.5">Created</th>
                      <th className="px-3 py-2.5 text-right">Actions</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-hairline bg-panel">
                    {docList.documents.map((doc: DocumentItem) => (
                      <tr key={doc.id} className="hover:bg-raised/50 transition-colors">
                        <td className="px-4 py-3">
                          <div className="flex items-center gap-2 max-w-xs sm:max-w-md">
                            {getFileTypeIcon(doc.file_type)}
                            <div className="truncate">
                              {doc.source_url ? (
                                <a
                                  href={doc.source_url}
                                  target="_blank"
                                  rel="noreferrer"
                                  className="text-accent-phosphor hover:underline font-medium truncate block"
                                >
                                  {doc.filename}
                                </a>
                              ) : (
                                <span className="font-medium text-ink-primary truncate block">{doc.filename}</span>
                              )}
                              <span className="text-[10px] font-mono text-ink-muted">{doc.doc_id}</span>
                            </div>
                          </div>
                        </td>
                        <td className="px-3 py-3">
                          <Badge tone="neutral">{doc.file_type.toUpperCase()}</Badge>
                        </td>
                        <td className="px-3 py-3">
                          <Badge tone={doc.status === "indexed" ? "green" : doc.status === "processing" ? "amber" : "red"}>
                            {doc.status}
                          </Badge>
                        </td>
                        <td className="px-3 py-3 font-mono text-ink-primary font-medium">{doc.chunk_count}</td>
                        <td className="px-3 py-3 text-ink-muted">{formatBytes(doc.file_size)}</td>
                        <td className="px-3 py-3 text-ink-muted whitespace-nowrap">
                          {new Date(doc.created_at).toLocaleDateString(undefined, {
                            month: "short",
                            day: "numeric",
                            hour: "2-digit",
                            minute: "2-digit",
                          })}
                        </td>
                        <td className="px-3 py-3 text-right">
                          <Button
                            variant="secondary"
                            size="sm"
                            onClick={() => handleDeleteDocument(doc.id, doc.filename)}
                            disabled={deletingId === doc.id}
                            className="text-signal-red hover:bg-signal-red/10 border-signal-red/20"
                          >
                            {deletingId === doc.id ? (
                              <Spinner />
                            ) : (
                              <Trash2 className="h-3.5 w-3.5" />
                            )}
                          </Button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </CardBody>
        </Card>

        {/* ============================================================ */}
        {/* SECTION 3: SYSTEM HEALTH & SAMPLE DATA LOADER */}
        {/* ============================================================ */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <Card>
            <CardHeader className="flex items-center gap-2">
              <HeartPulse className="h-4 w-4 text-accent-phosphor" />
              <span className="text-sm font-medium text-ink-primary">System Health</span>
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
                  <div className="flex flex-col gap-1.5 mt-1">
                    {health.services.map((s) => (
                      <div key={s.name} className="flex items-center justify-between text-xs">
                        <span className="text-ink-primary capitalize">{s.name}</span>
                        <Badge tone={s.healthy ? "green" : "red"}>{s.healthy ? "connected" : "down"}</Badge>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </CardBody>
          </Card>

          <Card>
            <CardHeader className="flex items-center gap-2">
              <Database className="h-4 w-4 text-ink-muted" />
              <span className="text-sm font-medium text-ink-primary">Sample Documents Directory</span>
            </CardHeader>
            <CardBody className="flex flex-col gap-3">
              <p className="text-xs text-ink-muted">
                Quickly index sample test files from local disk directory.
              </p>
              <div className="flex gap-2">
                <input
                  value={directory}
                  onChange={(e) => setDirectory(e.target.value)}
                  placeholder="data/sample_documents"
                  className="flex-1 rounded-md border border-hairline bg-raised px-3 py-2 text-xs font-mono text-ink-primary placeholder:text-ink-muted focus:outline-none focus-visible:ring-2 focus-visible:ring-accent-phosphor"
                />
                <Button onClick={runIndexDirectory} disabled={indexingDir} size="sm">
                  {indexingDir && <Spinner />}
                  {indexingDir ? "Indexing…" : "Index Dir"}
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
    </div>
  );
}
