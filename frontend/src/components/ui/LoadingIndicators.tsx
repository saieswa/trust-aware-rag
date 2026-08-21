"use client";

import { STAGE_LABELS } from "@/hooks/useChat";
import type { PipelineStage } from "@/types/api";

const STAGE_ORDER: PipelineStage[] = ["retrieving", "critiquing", "scoring", "synthesizing", "verifying", "done"];

/**
 * Shows the real pipeline stages (matching the actual agent graph nodes)
 * as a progressing readout — an instrument-panel status strip, not a
 * generic spinner, so the wait communicates what's actually happening:
 * retrieval, critique, trust scoring, synthesis, verification.
 */
export function PipelineProgress({ currentStage }: { currentStage: PipelineStage }) {
  const currentIndex = STAGE_ORDER.indexOf(currentStage);

  return (
    <div className="flex flex-col gap-2 rounded-md border border-hairline bg-raised/40 px-4 py-3">
      <div className="flex items-center gap-1.5">
        {STAGE_ORDER.slice(0, 5).map((stage, i) => (
          <div
            key={stage}
            className={
              "h-1 flex-1 rounded-full transition-colors duration-300 " +
              (i < currentIndex
                ? "bg-signal-green"
                : i === currentIndex
                  ? "bg-accent-phosphor animate-pulse"
                  : "bg-hairline")
            }
          />
        ))}
      </div>
      <span className="font-mono text-xs text-ink-muted">{STAGE_LABELS[currentStage]}…</span>
    </div>
  );
}

/** Small inline spinner for buttons and compact loading states. */
export function Spinner({ className = "" }: { className?: string }) {
  return (
    <svg className={`animate-spin ${className}`} width="16" height="16" viewBox="0 0 24 24" fill="none">
      <circle cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="3" opacity="0.25" />
      <path d="M22 12a10 10 0 0 0-10-10" stroke="currentColor" strokeWidth="3" strokeLinecap="round" />
    </svg>
  );
}
