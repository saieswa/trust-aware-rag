"use client";

import { CheckCircle2, XCircle, ShieldAlert } from "lucide-react";
import { AnswerText } from "@/components/chat/AnswerText";
import { PipelineProgress } from "@/components/ui/LoadingIndicators";
import { ErrorAlert } from "@/components/ui/ErrorAlert";
import { TrustGauge } from "@/components/ui/TrustGauge";
import { Badge } from "@/components/ui/Badge";
import { useTypewriter } from "@/hooks/useTypewriter";
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
      <div className="self-start max-w-[85%] w-full">
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
  const revealed = useTypewriter(result.final_answer);
  const isFullyRevealed = revealed.length >= result.final_answer.length;

  const StatusIcon =
    result.status === "approved" ? CheckCircle2 : result.status === "abstained" ? ShieldAlert : XCircle;
  const statusTone =
    result.status === "approved" ? "text-signal-green" : result.status === "abstained" ? "text-accent-phosphor" : "text-signal-red";

  return (
    <div className="rounded-lg rounded-bl-sm border border-hairline bg-panel px-4 py-3">
      <div className="flex items-start justify-between gap-3 mb-2">
        <div className={`flex items-center gap-1.5 text-xs font-mono ${statusTone}`}>
          <StatusIcon className="h-3.5 w-3.5" />
          {result.status === "approved" && "Verified answer"}
          {result.status === "abstained" && "Abstained"}
          {result.status === "verification_failed" && "Verification failed"}
        </div>
        {result.status !== "abstained" && <TrustGauge score={1 - result.hallucination_ratio} size="compact" />}
      </div>

      <AnswerText text={revealed} onCitationClick={onViewEvidence} />

      {isFullyRevealed && result.citations.length > 0 && (
        <div className="mt-3 flex flex-wrap gap-1.5 border-t border-hairline pt-3">
          {result.citations.map((c) => (
            <Badge key={c.chunk_id} tone="neutral" className="cursor-pointer" onClick={() => onViewEvidence(c.chunk_id)}>
              {c.source_title}
            </Badge>
          ))}
        </div>
      )}

      {isFullyRevealed && result.retry_count > 0 && (
        <p className="mt-2 text-xs text-ink-muted">
          Self-corrected after {result.retry_count} verification {result.retry_count === 1 ? "attempt" : "attempts"}.
        </p>
      )}
    </div>
  );
}
