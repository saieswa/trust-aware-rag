"use client";

import { useEffect, useRef } from "react";
import { useRouter } from "next/navigation";
import { ChatMessage } from "@/components/chat/ChatMessage";
import { ChatInput } from "@/components/chat/ChatInput";
import { useChat } from "@/hooks/useChat";

export default function ChatPage() {
  const { turns, submitQuery, retryTurn } = useChat();
  const router = useRouter();
  const scrollRef = useRef<HTMLDivElement>(null);
  const isPending = turns.some((t) => t.status === "pending");

  useEffect(() => {
    scrollRef.current?.scrollIntoView({ behavior: "smooth", block: "end" });
  }, [turns]);

  const handleViewEvidence = (chunkId: string) => {
    router.push(`/evidence?chunk=${encodeURIComponent(chunkId)}`);
  };

  return (
    <div className="flex h-screen flex-col">
      <header className="border-b border-hairline px-6 py-4">
        <h1 className="font-mono text-sm font-semibold text-ink-primary">Chat</h1>
        <p className="text-xs text-ink-muted mt-0.5">Answers are generated only from indexed, verified evidence.</p>
      </header>

      <div className="flex-1 overflow-y-auto px-6 py-6">
        {turns.length === 0 ? (
          <EmptyState />
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
        <ChatInput onSubmit={submitQuery} disabled={isPending} />
      </div>
    </div>
  );
}

function EmptyState() {
  return (
    <div className="mx-auto flex max-w-md flex-col items-center gap-2 pt-20 text-center">
      <p className="font-mono text-sm text-ink-primary">Nothing asked yet</p>
      <p className="text-xs text-ink-muted">
        Try a question about whatever you&rsquo;ve indexed in Admin — the answer will show its evidence and trust
        score inline.
      </p>
    </div>
  );
}
