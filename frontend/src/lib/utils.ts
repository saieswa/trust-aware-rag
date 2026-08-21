import { clsx, type ClassValue } from "clsx";
import type { Decision, EvidenceLabel } from "@/types/api";

/** Thin wrapper around clsx — kept as its own function so every component
 * imports from one place, making it trivial to swap in tailwind-merge
 * later if class conflicts ever become an issue. */
export function cn(...inputs: ClassValue[]) {
  return clsx(inputs);
}

/** Trust score thresholds — mirrors backend .env defaults
 * (TRUST_THRESHOLD_HIGH / TRUST_THRESHOLD_LOW). The backend is the source
 * of truth for the actual decision; these are only used for client-side
 * display (e.g. gauge tick marks) when we already have a numeric score
 * but want to render thresholds without waiting on another field. */
export const TRUST_THRESHOLD_HIGH = 0.75;
export const TRUST_THRESHOLD_LOW = 0.5;

export function decisionLabel(decision: Decision): string {
  switch (decision) {
    case "answer":
      return "Answer";
    case "retrieve_more":
      return "Needs more evidence";
    case "abstain":
      return "Abstain";
  }
}

export function decisionColorVar(decision: Decision): string {
  switch (decision) {
    case "answer":
      return "var(--signal-green)";
    case "retrieve_more":
      return "var(--accent-phosphor)";
    case "abstain":
      return "var(--signal-red)";
  }
}

export function evidenceLabelColorVar(label: EvidenceLabel): string {
  switch (label) {
    case "support":
      return "var(--signal-green)";
    case "contradict":
      return "var(--signal-red)";
    case "neutral":
      return "var(--ink-muted)";
  }
}

export function formatPercent(value: number): string {
  return `${Math.round(value * 100)}%`;
}

export function formatScore(value: number): string {
  return value.toFixed(2);
}

/** Renders inline [chunk_id] citation markers as a lighter, monospace
 * span — used anywhere the Synthesizer's raw answer text is displayed. */
export function splitAnswerIntoParts(text: string): Array<{ type: "text" | "citation"; value: string }> {
  const parts: Array<{ type: "text" | "citation"; value: string }> = [];
  const pattern = /\[([a-zA-Z0-9_]+)\]/g;
  let lastIndex = 0;
  let match: RegExpExecArray | null;

  while ((match = pattern.exec(text)) !== null) {
    if (match.index > lastIndex) {
      parts.push({ type: "text", value: text.slice(lastIndex, match.index) });
    }
    parts.push({ type: "citation", value: match[1] });
    lastIndex = pattern.lastIndex;
  }
  if (lastIndex < text.length) {
    parts.push({ type: "text", value: text.slice(lastIndex) });
  }
  return parts;
}
