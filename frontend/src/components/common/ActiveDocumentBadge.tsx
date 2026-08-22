"use client";

import { useEffect, useState } from "react";
import { FileText, Check, ChevronDown } from "lucide-react";
import { api } from "@/lib/api";
import type { DocumentItem } from "@/types/api";

interface ActiveDocumentBadgeProps {
  activeDocId?: string;
  onDocChange?: (doc: DocumentItem) => void;
}

export function ActiveDocumentBadge({ activeDocId, onDocChange }: ActiveDocumentBadgeProps) {
  const [documents, setDocuments] = useState<DocumentItem[]>([]);
  const [activeDoc, setActiveDoc] = useState<DocumentItem | null>(null);
  const [open, setOpen] = useState(false);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    loadDocs();
  }, [activeDocId]);

  const loadDocs = async () => {
    try {
      const [listRes, activeRes] = await Promise.all([
        api.listDocuments(),
        api.getActiveDocument(),
      ]);
      setDocuments(listRes.documents);
      if (activeDocId) {
        const found = listRes.documents.find((d) => d.doc_id === activeDocId);
        setActiveDoc(found || activeRes);
      } else {
        setActiveDoc(activeRes);
      }
    } catch {
      // ignore
    }
  };

  const handleSelect = async (doc: DocumentItem) => {
    setLoading(true);
    try {
      const updated = await api.activateDocument(doc.doc_id);
      setActiveDoc(updated);
      onDocChange?.(updated);
      setOpen(false);
    } catch {
      // ignore
    } finally {
      setLoading(false);
    }
  };

  if (!activeDoc && documents.length === 0) {
    return (
      <div className="flex items-center gap-1.5 rounded-full border border-amber-500/20 bg-amber-500/10 px-2.5 py-1 text-xs text-amber-300">
        <FileText className="h-3 w-3" />
        <span>No document indexed</span>
      </div>
    );
  }

  return (
    <div className="relative inline-block text-left">
      <button
        onClick={() => setOpen(!open)}
        className="flex items-center gap-2 rounded-md border border-hairline bg-raised hover:bg-panel px-3 py-1.5 text-xs text-ink-primary transition-colors focus:outline-none focus-visible:ring-1 focus-visible:ring-accent-phosphor"
      >
        <span className="h-2 w-2 rounded-full bg-emerald-400 animate-pulse" />
        <span className="font-mono text-ink-muted">Active Doc:</span>
        <span className="font-medium max-w-[200px] truncate text-ink-primary">
          {activeDoc?.filename || "Select Document"}
        </span>
        <ChevronDown className="h-3 w-3 text-ink-muted ml-0.5" />
      </button>

      {open && (
        <>
          <div className="fixed inset-0 z-40" onClick={() => setOpen(false)} />
          <div className="absolute right-0 mt-1.5 w-72 rounded-lg border border-hairline bg-panel p-1.5 shadow-xl z-50">
            <div className="px-2 py-1.5 text-[11px] font-semibold uppercase tracking-wider text-ink-muted border-b border-hairline mb-1">
              Switch Target Document
            </div>
            <div className="max-h-60 overflow-y-auto flex flex-col gap-0.5">
              {documents.map((doc) => {
                const isSelected = doc.doc_id === activeDoc?.doc_id;
                return (
                  <button
                    key={doc.id}
                    onClick={() => handleSelect(doc)}
                    disabled={loading}
                    className={`flex items-center justify-between w-full rounded px-2.5 py-2 text-left text-xs transition-colors ${
                      isSelected
                        ? "bg-accent-phosphor/15 text-accent-phosphor font-medium"
                        : "text-ink-secondary hover:bg-raised hover:text-ink-primary"
                    }`}
                  >
                    <div className="flex flex-col truncate pr-2">
                      <span className="truncate">{doc.filename}</span>
                      <span className="font-mono text-[10px] text-ink-muted">{doc.doc_id} • {doc.chunk_count} chunks</span>
                    </div>
                    {isSelected && <Check className="h-3.5 w-3.5 shrink-0 text-accent-phosphor" />}
                  </button>
                );
              })}
            </div>
          </div>
        </>
      )}
    </div>
  );
}
