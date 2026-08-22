"use client";

import { useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { ChatMessage } from "@/components/chat/ChatMessage";
import { ChatInput } from "@/components/chat/ChatInput";
import { ActiveDocumentBadge } from "@/components/common/ActiveDocumentBadge";
import { useChat } from "@/hooks/useChat";
import type { DocumentItem } from "@/types/api";

export default function ChatPage() {
  const [activeDoc, setActiveDoc] = useState<DocumentItem | null>(null);
  const { turns, submitQuery, retryTurn, clearChat } = useChat(activeDoc?.doc_id);
  const router = useRouter();
  const scrollRef = useRef<HTMLDivElement>(null);
  const isPending = turns.some((t) => t.status === "pending");

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
          <h1 className="font-mono text-sm font-semibold text-ink-primary">Chat</h1>
          <p className="text-xs text-ink-muted mt-0.5">
            Answers are generated strictly from the active document with sentence-level verification.
          </p>
        </div>
        <ActiveDocumentBadge activeDocId={activeDoc?.doc_id} onDocChange={handleDocChange} />
      </header>

      <div className="flex-1 overflow-y-auto px-6 py-6">
        {turns.length === 0 ? (
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
          disabled={isPending}
          placeholder={
            activeDoc
              ? `Ask a question about "${activeDoc.filename}"...`
              : "Ask a question about the active document..."
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
