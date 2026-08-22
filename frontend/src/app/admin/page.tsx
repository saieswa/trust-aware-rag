"use client";

import { useEffect, useRef, useState } from "react";
import {
  AlertCircle,
  CheckCircle2,
  Check,
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
  Zap,
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
  const [activeDoc, setActiveDoc] = useState<DocumentItem | null>(null);
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

  // Document actions state
  const [deletingId, setDeletingId] = useState<string | null>(null);
  const [activatingDocId, setActivatingDocId] = useState<string | null>(null);
  const [reindexingAll, setReindexingAll] = useState(false);

  const loadAll = async () => {
    setError(null);
    setLoading(true);
    try {
      const [healthData, statsData, documentsData, activeData] = await Promise.all([
        api.health().catch(() => null),
        api.retrievalStats().catch(() => null),
        api.listDocuments().catch(() => null),
        api.getActiveDocument().catch(() => null),
      ]);
      if (healthData) setHealth(healthData);
      if (statsData) setStats(statsData);
      if (documentsData) setDocList(documentsData);
      if (activeData) setActiveDoc(activeData);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Couldn't load admin data.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadAll();
  }, []);

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
        const res = await api.uploadDocument(file);
        setActiveDoc(res.document);
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

  const handleIngestUrl = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!urlInput.trim()) return;

    setIngestingUrl(true);
    setError(null);
    setSuccessMessage(null);

    try {
      const res = await api.ingestUrl(urlInput.trim());
      setActiveDoc(res.document);
      setSuccessMessage(`Successfully fetched and indexed ${res.document.filename} (${res.document.chunk_count} chunks).`);
      setUrlInput("");
      await loadAll();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to ingest URL.");
    } finally {
      setIngestingUrl(false);
    }
  };

  const handleActivateDocument = async (docId: string, filename: string) => {
    setActivatingDocId(docId);
    setError(null);
    try {
      const updated = await api.activateDocument(docId);
      setActiveDoc(updated);
      setSuccessMessage(`Active document set to "${filename}". Chat and Evidence will now search this document exclusively.`);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to activate document.");
    } finally {
      setActivatingDocId(null);
    }
  };

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

  return (
    <div className="mx-auto max-w-4xl px-6 py-8">
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="font-mono text-sm font-semibold text-ink-primary">Admin & Knowledge Base</h1>
          <p className="text-xs text-ink-muted mt-0.5">
            Add knowledge sources, manage active research documents, and monitor database health.
          </p>
        </div>
        <Button variant="secondary" size="sm" onClick={loadAll} disabled={loading}>
          <RefreshCw className={`h-3.5 w-3.5 ${loading ? "animate-spin" : ""}`} />
          Refresh
        </Button>
      </div>

      {/* Notifications */}
      {successMessage && (
        <div className="mb-6 flex items-center justify-between rounded-md border border-emerald-500/20 bg-emerald-500/10 px-4 py-3 text-xs text-emerald-300">
          <div className="flex items-center gap-2">
            <CheckCircle2 className="h-4 w-4 shrink-0 text-emerald-400" />
            <span>{successMessage}</span>
          </div>
          <button onClick={() => setSuccessMessage(null)} className="text-ink-muted hover:text-ink-primary">
            <X className="h-3.5 w-3.5" />
          </button>
        </div>
      )}

      {error && <ErrorAlert message={error} onRetry={loadAll} className="mb-6" />}

      <div className="flex flex-col gap-6">
        {/* ============================================================ */}
        {/* SECTION 0: ACTIVE DOCUMENT STATUS BANNER */}
        {/* ============================================================ */}
        {activeDoc && (
          <div className="rounded-lg border border-emerald-500/30 bg-emerald-950/20 p-4">
            <div className="flex items-center justify-between mb-2">
              <div className="flex items-center gap-2">
                <span className="h-2 w-2 rounded-full bg-emerald-400 animate-pulse" />
                <span className="font-mono text-xs font-semibold uppercase tracking-wider text-emerald-400">
                  Currently Selected Document
                </span>
              </div>
              <Badge tone="green">INDEXED</Badge>
            </div>
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 pt-1">
              <div>
                <p className="text-[11px] text-ink-muted uppercase">Document Name</p>
                <p className="text-sm font-medium text-ink-primary truncate mt-0.5">{activeDoc.filename}</p>
              </div>
              <div>
                <p className="text-[11px] text-ink-muted uppercase">Document ID</p>
                <p className="font-mono text-xs text-accent-phosphor truncate mt-0.5">{activeDoc.doc_id}</p>
              </div>
              <div>
                <p className="text-[11px] text-ink-muted uppercase">Chunks / Vectors</p>
                <p className="font-mono text-sm font-semibold text-signal-green mt-0.5">{activeDoc.chunk_count} chunks</p>
              </div>
            </div>
          </div>
        )}

        {/* ============================================================ */}
        {/* SECTION 1: ADD KNOWLEDGE / DOCUMENT INGESTION */}
        {/* ============================================================ */}
        <Card>
          <CardHeader className="flex items-center gap-2">
            <Plus className="h-4 w-4 text-accent-phosphor" />
            <span className="text-sm font-medium text-ink-primary">Add Knowledge / Upload Documents</span>
          </CardHeader>
          <CardBody className="flex flex-col gap-5">
            <div>
              <label className="text-xs font-semibold text-ink-primary mb-1.5 block">
                Upload Files ({SUPPORTED_EXTS.join(", ")})
              </label>

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
                className={`flex flex-col items-center justify-center rounded-lg border-2 border-dashed p-6 cursor-pointer transition-colors ${
                  isDragging
                    ? "border-accent-phosphor bg-accent-phosphor/10"
                    : "border-hairline bg-raised hover:bg-panel hover:border-hairline-bright"
                }`}
              >
                <Upload className="h-8 w-8 text-ink-muted mb-2" />
                <p className="text-xs font-medium text-ink-primary">
                  Click to select or drag and drop files here
                </p>
                <p className="text-[11px] text-ink-muted mt-1">
                  Supports PDF research papers, TXT, DOCX, CSV, JSON datasets (Max 25MB)
                </p>
                <input
                  ref={fileInputRef}
                  type="file"
                  multiple
                  accept={SUPPORTED_EXTS.join(",")}
                  className="hidden"
                  onChange={(e) => handleFileSelect(e.target.files)}
                />
              </div>

              {selectedFiles.length > 0 && (
                <div className="mt-3 flex flex-col gap-2">
                  <div className="text-xs font-mono text-ink-muted">Selected files ready to index:</div>
                  <div className="flex flex-wrap gap-2">
                    {selectedFiles.map((file, idx) => (
                      <div
                        key={idx}
                        className="flex items-center gap-2 rounded bg-panel border border-hairline px-3 py-1.5 text-xs text-ink-primary"
                      >
                        <span className="truncate max-w-[200px]">{file.name}</span>
                        <span className="text-[10px] text-ink-muted font-mono">{formatBytes(file.size)}</span>
                        <button
                          type="button"
                          onClick={(e) => {
                            e.stopPropagation();
                            handleRemoveFile(idx);
                          }}
                          className="text-ink-muted hover:text-signal-red"
                        >
                          <X className="h-3.5 w-3.5" />
                        </button>
                      </div>
                    ))}
                  </div>
                  <div className="pt-2 flex justify-end">
                    <Button onClick={handleUploadFiles} disabled={uploading}>
                      {uploading ? <Spinner /> : <Upload className="h-3.5 w-3.5" />}
                      {uploading ? "Processing & Indexing…" : `Upload & Index (${selectedFiles.length})`}
                    </Button>
                  </div>
                </div>
              )}
            </div>

            <div className="border-t border-hairline pt-4">
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
                  Upload a PDF research paper or paste a URL above to populate your knowledge base.
                </p>
              </div>
            ) : (
              <div className="overflow-x-auto rounded-md border border-hairline">
                <table className="w-full text-left text-xs">
                  <thead className="border-b border-hairline bg-raised font-mono text-[11px] uppercase tracking-wider text-ink-muted">
                    <tr>
                      <th className="px-4 py-2.5">Document / Source</th>
                      <th className="px-3 py-2.5">Type</th>
                      <th className="px-3 py-2.5">Active Scope</th>
                      <th className="px-3 py-2.5">Chunks</th>
                      <th className="px-3 py-2.5">Size</th>
                      <th className="px-3 py-2.5 text-right">Actions</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-hairline bg-panel">
                    {docList.documents.map((doc: DocumentItem) => {
                      const isActive = doc.doc_id === activeDoc?.doc_id;
                      return (
                        <tr
                          key={doc.id}
                          className={`transition-colors ${
                            isActive ? "bg-emerald-950/20" : "hover:bg-raised/50"
                          }`}
                        >
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
                            {isActive ? (
                              <Badge tone="green">ACTIVE</Badge>
                            ) : (
                              <Button
                                variant="secondary"
                                size="sm"
                                onClick={() => handleActivateDocument(doc.doc_id, doc.filename)}
                                disabled={activatingDocId === doc.doc_id}
                                className="h-6 text-[11px] px-2"
                              >
                                <Zap className="h-3 w-3 mr-1 text-accent-phosphor" />
                                Activate
                              </Button>
                            )}
                          </td>
                          <td className="px-3 py-3 font-mono text-ink-primary font-medium">{doc.chunk_count}</td>
                          <td className="px-3 py-3 text-ink-muted">{formatBytes(doc.file_size)}</td>
                          <td className="px-3 py-3 text-right">
                            <Button
                              variant="secondary"
                              size="sm"
                              onClick={() => handleDeleteDocument(doc.id, doc.filename)}
                              disabled={deletingId === doc.id}
                              className="text-signal-red hover:bg-signal-red/10"
                            >
                              <Trash2 className="h-3 w-3" />
                            </Button>
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            )}
          </CardBody>
        </Card>

        {/* ============================================================ */}
        {/* SECTION 3: SYSTEM HEALTH & CLOUD CONNECTIONS */}
        {/* ============================================================ */}
        <Card>
          <CardHeader className="flex items-center gap-2">
            <HeartPulse className="h-4 w-4 text-signal-green" />
            <span className="text-sm font-medium text-ink-primary">System Health &amp; Services</span>
          </CardHeader>
          <CardBody className="flex flex-col gap-3">
            <div className="flex items-center justify-between">
              <span className="text-xs text-ink-muted">Overall API Status</span>
              <Badge tone={health?.status === "ok" ? "green" : "red"}>{health?.status ?? "unknown"}</Badge>
            </div>
            {health?.services.map((svc) => (
              <div
                key={svc.name}
                className="flex items-center justify-between border-t border-hairline pt-2 text-xs"
              >
                <div className="flex items-center gap-2">
                  <div
                    className={`h-2 w-2 rounded-full ${
                      svc.healthy ? "bg-signal-green" : "bg-signal-red"
                    }`}
                  />
                  <span className="font-mono text-ink-primary">{svc.name}</span>
                </div>
                <span className="text-[11px] text-ink-muted">{svc.detail ?? (svc.healthy ? "connected" : "unreachable")}</span>
              </div>
            ))}
          </CardBody>
        </Card>
      </div>
    </div>
  );
}
