"use client";

import { CheckCircle2, XCircle, ShieldAlert } from "lucide-react";
import { StructuredAnswerViewer } from "@/components/chat/StructuredAnswerViewer";
import { PipelineProgress } from "@/components/ui/LoadingIndicators";
import { ErrorAlert } from "@/components/ui/ErrorAlert";
import { TrustGauge } from "@/components/ui/TrustGauge";
import { Badge } from "@/components/ui/Badge";
import type { ChatTurn } from "@/types/api";

interface ChatMessageProps {
  turn: ChatTurn;
  onRetry: (id: string) => void;
  onViewEvidence: (chunkId: string) => void;
}

export function ChatMessage({ turn, onRetry, onViewEvidence }: ChatMessageProps) {
  return (
    <div className="flex flex-col gap-3 animate-fade-up">
      {/* User's question */}
      <div className="self-end max-w-[80%] rounded-lg rounded-br-sm bg-accent-phosphor/10 border border-accent-phosphor/20 px-4 py-2.5">
        <p className="text-sm text-ink-primary">{turn.query}</p>
      </div>

      {/* Assistant's response */}
      <div className="self-start max-w-[90%] w-full">
        {turn.status === "pending" && turn.stage && <PipelineProgress currentStage={turn.stage} />}

        {turn.status === "error" && (
          <ErrorAlert message={turn.errorMessage || "Something went wrong."} onRetry={() => onRetry(turn.id)} />
        )}

        {turn.status === "done" && turn.result && <ResolvedAnswer turn={turn} onViewEvidence={onViewEvidence} />}
      </div>
    </div>
  );
}

function ResolvedAnswer({ turn, onViewEvidence }: { turn: ChatTurn; onViewEvidence: (chunkId: string) => void }) {
  const result = turn.result!;

  const StatusIcon =
    result.status === "approved" ? CheckCircle2 : result.status === "abstained" ? ShieldAlert : XCircle;
  const statusTone =
    result.status === "approved" ? "text-signal-green" : result.status === "abstained" ? "text-accent-phosphor" : "text-signal-red";

  return (
    <div className="rounded-lg rounded-bl-sm border border-hairline bg-panel px-4 py-3.5 shadow-sm">
      <div className="flex items-start justify-between gap-3 mb-3 border-b border-hairline pb-2.5">
        <div className={`flex items-center gap-1.5 text-xs font-mono font-medium ${statusTone}`}>
          <StatusIcon className="h-4 w-4" />
          {result.status === "approved" && "Verified answer"}
          {result.status === "abstained" && "Abstained"}
          {result.status === "verification_failed" && "Verification failed"}
        </div>
        {result.status !== "abstained" && <TrustGauge score={1 - result.hallucination_ratio} size="compact" />}
      </div>

      {/* Structured / Clean Content Rendering */}
      <StructuredAnswerViewer
        structuredAnswer={result.structured_answer}
        rawText={result.final_answer}
        onCitationClick={onViewEvidence}
      />

      {result.citations.length > 0 && (
        <div className="mt-4 flex flex-wrap items-center gap-1.5 border-t border-hairline pt-3">
          <span className="text-[11px] text-ink-muted mr-1">Sources:</span>
          {result.citations.map((c) => (
            <Badge key={c.chunk_id} tone="neutral" className="cursor-pointer text-xs" onClick={() => onViewEvidence(c.chunk_id)}>
              {c.source_title}
            </Badge>
          ))}
        </div>
      )}

      {result.retry_count > 0 && (
        <p className="mt-2 text-xs text-ink-muted">
          Self-corrected after {result.retry_count} verification {result.retry_count === 1 ? "attempt" : "attempts"}.
        </p>
      )}
    </div>
  );
}
