"use client";

import { useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { FileText, AlertCircle } from "lucide-react";
import { ChatMessage } from "@/components/chat/ChatMessage";
import { ChatInput } from "@/components/chat/ChatInput";
import { ActiveDocumentBadge } from "@/components/common/ActiveDocumentBadge";
import { useChat } from "@/hooks/useChat";
import { api } from "@/lib/api";
import type { DocumentItem } from "@/types/api";

export default function ChatPage() {
  const [activeDoc, setActiveDoc] = useState<DocumentItem | null>(null);
  const [initialLoading, setInitialLoading] = useState(true);
  const { turns, submitQuery, retryTurn, clearChat } = useChat(activeDoc?.doc_id);
  const router = useRouter();
  const scrollRef = useRef<HTMLDivElement>(null);
  const isPending = turns.some((t) => t.status === "pending");

  useEffect(() => {
    api
      .getActiveDocument()
      .then((doc) => setActiveDoc(doc))
      .catch(() => setActiveDoc(null))
      .finally(() => setInitialLoading(false));
  }, []);

  useEffect(() => {
    scrollRef.current?.scrollIntoView({ behavior: "smooth", block: "end" });
  }, [turns]);

  const handleDocChange = (doc: DocumentItem) => {
    setActiveDoc(doc);
    clearChat();
  };

  const handleViewEvidence = (chunkId: string) => {
    router.push(`/evidence?chunk=${encodeURIComponent(chunkId)}`);
  };

  return (
    <div className="flex h-screen flex-col">
      <header className="border-b border-hairline px-6 py-3.5 flex items-center justify-between">
        <div>
          <div className="flex items-center gap-2">
            <h1 className="font-mono text-sm font-semibold text-ink-primary">Chat</h1>
            {activeDoc && (
              <span className="flex items-center gap-1.5 text-xs text-ink-muted bg-raised px-2 py-0.5 rounded border border-hairline">
                <FileText className="h-3 w-3 text-accent-phosphor" />
                <span>Current document:</span>
                <span className="font-medium text-ink-primary max-w-[220px] truncate">
                  {activeDoc.filename}
                </span>
              </span>
            )}
          </div>
          <p className="text-xs text-ink-muted mt-0.5">
            Answers are generated strictly from the current document with sentence-level verification.
          </p>
        </div>
        <ActiveDocumentBadge activeDocId={activeDoc?.doc_id} onDocChange={handleDocChange} />
      </header>

      <div className="flex-1 overflow-y-auto px-6 py-6">
        {!initialLoading && !activeDoc && turns.length === 0 ? (
          <div className="mx-auto flex max-w-md flex-col items-center gap-2 pt-20 text-center">
            <AlertCircle className="h-8 w-8 text-amber-400 mb-1" />
            <p className="font-mono text-sm text-ink-primary">No document indexed</p>
            <p className="text-xs text-ink-muted">
              Please go to the <strong>Admin</strong> page to upload a research paper or activate an existing document before starting a chat.
            </p>
          </div>
        ) : turns.length === 0 ? (
          <EmptyState filename={activeDoc?.filename} />
        ) : (
          <div className="mx-auto flex max-w-3xl flex-col gap-6">
            {turns.map((turn) => (
              <ChatMessage key={turn.id} turn={turn} onRetry={retryTurn} onViewEvidence={handleViewEvidence} />
            ))}
            <div ref={scrollRef} />
          </div>
        )}
      </div>

      <div className="mx-auto w-full max-w-3xl">
        <ChatInput
          onSubmit={submitQuery}
          disabled={isPending || !activeDoc}
          placeholder={
            activeDoc
              ? `Ask a question about "${activeDoc.filename}"...`
              : "No document active — please upload or select a document in Admin"
          }
        />
      </div>
    </div>
  );
}

function EmptyState({ filename }: { filename?: string }) {
  return (
    <div className="mx-auto flex max-w-md flex-col items-center gap-2 pt-20 text-center">
      <p className="font-mono text-sm text-ink-primary">
        {filename ? `Ready to answer questions from ${filename}` : "Nothing asked yet"}
      </p>
      <p className="text-xs text-ink-muted">
        Ask questions like &ldquo;What is the title of this paper?&rdquo;, &ldquo;What is the problem statement?&rdquo;, or &ldquo;What are the main results?&rdquo;.
        Answers will include verified citations and trust diagnostics.
      </p>
    </div>
  );
}
