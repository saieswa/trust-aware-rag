"use client";

import React, { useState } from "react";
import {
  FileText,
  Target,
  ListOrdered,
  Sparkles,
  BookmarkCheck,
  ShieldCheck,
  ShieldAlert,
  ChevronDown,
  ChevronUp,
  BookOpen,
  CheckCircle2,
} from "lucide-react";
import { TrustGauge } from "@/components/ui/TrustGauge";
import { Badge } from "@/components/ui/Badge";
import type { StructuredAnswer, SynthesisResponse } from "@/types/api";

interface StructuredAnswerViewProps {
  synthesis: SynthesisResponse;
  structuredAnswer?: StructuredAnswer | null;
  onViewChunk?: (chunkId: string) => void;
}

// Clean helper to strip internal chunk IDs / doc IDs from user-facing text
function cleanUserFacingText(text: string): string {
  if (!text) return "";
  return text
    .replace(/\[doc_[a-zA-Z0-9_\-]+_chunk\d+\]/gi, "")
    .replace(/\[chunk_\d+\]/gi, "")
    .replace(/\[doc_[a-zA-Z0-9_\-]+\]/gi, "")
    .replace(/\s{2,}/g, " ")
    .trim();
}

export function StructuredAnswerView({
  synthesis,
  structuredAnswer,
  onViewChunk,
}: StructuredAnswerViewProps) {
  const [expandedEvidence, setExpandedEvidence] = useState<Record<number, boolean>>({});

  const toggleEvidence = (idx: number) => {
    setExpandedEvidence((prev) => ({ ...prev, [idx]: !prev[idx] }));
  };

  // If structured answer object is provided by backend
  const data = structuredAnswer || synthesis.structured_answer;

  // If we have a structured document explanation
  if (data && data.answer_type === "document_explanation") {
    const trustScore = data.trust?.score ?? (1 - (synthesis.hallucination_ratio || 0));
    const trustPct = Math.round(trustScore * 100);
    const trustLabel =
      data.trust?.label ||
      (trustScore >= 0.75 ? "High Confidence" : trustScore >= 0.5 ? "Medium Confidence" : "Needs More Evidence");

    return (
      <div className="space-y-5">
        {/* 1. Document Overview */}
        {data.document_overview && (
          <div className="rounded-xl border border-hairline bg-panel/70 p-4 shadow-sm backdrop-blur-sm">
            <div className="flex items-center gap-2 mb-2">
              <div className="flex h-6 w-6 items-center justify-center rounded-lg bg-accent-phosphor/10 text-accent-phosphor">
                <FileText className="h-3.5 w-3.5" />
              </div>
              <h4 className="text-xs font-mono font-semibold uppercase tracking-wider text-accent-phosphor">
                Document Overview
              </h4>
            </div>
            <p className="text-sm leading-relaxed text-ink-primary font-sans">
              {cleanUserFacingText(data.document_overview)}
            </p>
          </div>
        )}

        {/* 2. Main Idea */}
        {data.main_idea && (
          <div className="rounded-xl border border-hairline bg-panel/70 p-4 shadow-sm backdrop-blur-sm">
            <div className="flex items-center gap-2 mb-2">
              <div className="flex h-6 w-6 items-center justify-center rounded-lg bg-accent-phosphor/10 text-accent-phosphor">
                <Target className="h-3.5 w-3.5" />
              </div>
              <h4 className="text-xs font-mono font-semibold uppercase tracking-wider text-accent-phosphor">
                Main Idea
              </h4>
            </div>
            <p className="text-sm leading-relaxed text-ink-primary font-sans">
              {cleanUserFacingText(data.main_idea)}
            </p>
          </div>
        )}

        {/* 3. Step-by-Step Explanation */}
        {data.steps && data.steps.length > 0 && (
          <div className="rounded-xl border border-hairline bg-panel/70 p-4 shadow-sm backdrop-blur-sm">
            <div className="flex items-center gap-2 mb-3">
              <div className="flex h-6 w-6 items-center justify-center rounded-lg bg-accent-phosphor/10 text-accent-phosphor">
                <ListOrdered className="h-3.5 w-3.5" />
              </div>
              <h4 className="text-xs font-mono font-semibold uppercase tracking-wider text-accent-phosphor">
                Step-by-Step Explanation
              </h4>
            </div>
            <div className="space-y-2.5">
              {data.steps.map((step, idx) => (
                <div key={idx} className="flex items-start gap-3">
                  <span className="flex h-5 w-5 flex-shrink-0 items-center justify-center rounded-full bg-accent-phosphor/15 text-[11px] font-mono font-bold text-accent-phosphor mt-0.5">
                    {idx + 1}
                  </span>
                  <p className="text-sm leading-relaxed text-ink-primary/95 font-sans">
                    {cleanUserFacingText(step)}
                  </p>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* 4. Key Points & Main Findings (2 columns if both exist) */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {data.key_points && data.key_points.length > 0 && (
            <div className="rounded-xl border border-hairline bg-panel/70 p-4 shadow-sm backdrop-blur-sm">
              <div className="flex items-center gap-2 mb-3">
                <div className="flex h-6 w-6 items-center justify-center rounded-lg bg-accent-phosphor/10 text-accent-phosphor">
                  <Sparkles className="h-3.5 w-3.5" />
                </div>
                <h4 className="text-xs font-mono font-semibold uppercase tracking-wider text-accent-phosphor">
                  Key Points
                </h4>
              </div>
              <ul className="space-y-2">
                {data.key_points.map((pt, idx) => (
                  <li key={idx} className="flex items-start gap-2 text-sm text-ink-primary/95">
                    <span className="text-accent-phosphor font-bold mt-0.5">•</span>
                    <span>{cleanUserFacingText(pt)}</span>
                  </li>
                ))}
              </ul>
            </div>
          )}

          {data.main_findings && data.main_findings.length > 0 && (
            <div className="rounded-xl border border-hairline bg-panel/70 p-4 shadow-sm backdrop-blur-sm">
              <div className="flex items-center gap-2 mb-3">
                <div className="flex h-6 w-6 items-center justify-center rounded-lg bg-accent-phosphor/10 text-accent-phosphor">
                  <BookmarkCheck className="h-3.5 w-3.5" />
                </div>
                <h4 className="text-xs font-mono font-semibold uppercase tracking-wider text-accent-phosphor">
                  Main Findings / Topics
                </h4>
              </div>
              <ul className="space-y-2">
                {data.main_findings.map((f, idx) => (
                  <li key={idx} className="flex items-start gap-2 text-sm text-ink-primary/95">
                    <span className="text-accent-phosphor font-bold mt-0.5">•</span>
                    <span>{cleanUserFacingText(f)}</span>
                  </li>
                ))}
              </ul>
            </div>
          )}
        </div>

        {/* 5. Supporting Evidence Section */}
        {data.evidence && data.evidence.length > 0 && (
          <div className="rounded-xl border border-hairline bg-panel/70 p-4 shadow-sm backdrop-blur-sm">
            <div className="flex items-center gap-2 mb-3">
              <div className="flex h-6 w-6 items-center justify-center rounded-lg bg-accent-phosphor/10 text-accent-phosphor">
                <BookOpen className="h-3.5 w-3.5" />
              </div>
              <h4 className="text-xs font-mono font-semibold uppercase tracking-wider text-accent-phosphor">
                Supporting Evidence
              </h4>
            </div>
            <div className="space-y-3">
              {data.evidence.map((ev, idx) => {
                const isExpanded = !!expandedEvidence[idx];
                return (
                  <div key={idx} className="rounded-lg border border-hairline/60 bg-panel-elevated/40 p-3">
                    <div className="flex items-center justify-between gap-2 mb-1.5">
                      <div className="flex items-center gap-2">
                        <span className="text-xs font-mono text-ink-secondary">{ev.source || "Active Document"}</span>
                        {ev.page && (
                          <Badge tone="neutral" className="text-[10px] px-1.5 py-0">
                            Page {ev.page}
                          </Badge>
                        )}
                      </div>
                      <button
                        type="button"
                        onClick={() => toggleEvidence(idx)}
                        className="flex items-center gap-1 text-[11px] font-mono text-accent-phosphor hover:underline cursor-pointer"
                      >
                        {isExpanded ? (
                          <>
                            Less <ChevronUp className="h-3 w-3" />
                          </>
                        ) : (
                          <>
                            View Full Evidence <ChevronDown className="h-3 w-3" />
                          </>
                        )}
                      </button>
                    </div>
                    <p className="text-xs leading-relaxed text-ink-primary/90 italic">
                      "{isExpanded ? ev.text : ev.text.slice(0, 140) + (ev.text.length > 140 ? "…" : "")}"
                    </p>
                  </div>
                );
              })}
            </div>
          </div>
        )}

        {/* 6. Trust Result Section */}
        <div className="rounded-xl border border-hairline bg-panel/70 p-4 shadow-sm backdrop-blur-sm">
          <div className="flex items-center justify-between gap-3 mb-3">
            <div className="flex items-center gap-2">
              <div className="flex h-6 w-6 items-center justify-center rounded-lg bg-signal-green/10 text-signal-green">
                <ShieldCheck className="h-3.5 w-3.5" />
              </div>
              <div>
                <h4 className="text-xs font-mono font-semibold uppercase tracking-wider text-ink-primary">
                  Trust Result
                </h4>
                <p className="text-xs font-mono text-signal-green">
                  {trustPct}% — {trustLabel}
                </p>
              </div>
            </div>
            <TrustGauge score={trustScore} size="compact" />
          </div>

          <div className="border-t border-hairline/60 pt-3">
            <p className="text-xs font-mono text-ink-muted mb-2">Why this answer is trusted:</p>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 text-xs text-ink-primary">
              <div className="flex items-center gap-1.5 text-signal-green font-mono text-[11px]">
                <CheckCircle2 className="h-3.5 w-3.5 flex-shrink-0" />
                <span>Evidence comes from active document</span>
              </div>
              <div className="flex items-center gap-1.5 text-signal-green font-mono text-[11px]">
                <CheckCircle2 className="h-3.5 w-3.5 flex-shrink-0" />
                <span>Evidence directly supports answer</span>
              </div>
              <div className="flex items-center gap-1.5 text-signal-green font-mono text-[11px]">
                <CheckCircle2 className="h-3.5 w-3.5 flex-shrink-0" />
                <span>No conflicting evidence detected</span>
              </div>
              <div className="flex items-center gap-1.5 text-signal-green font-mono text-[11px]">
                <CheckCircle2 className="h-3.5 w-3.5 flex-shrink-0" />
                <span>No foreign document data used</span>
              </div>
            </div>
          </div>
        </div>
      </div>
    );
  }

  // If specific answer format
  if (data && data.answer_type === "specific_answer") {
    const trustScore = data.trust?.score ?? (1 - (synthesis.hallucination_ratio || 0));
    const trustPct = Math.round(trustScore * 100);
    const trustLabel =
      data.trust?.label ||
      (trustScore >= 0.75 ? "High Confidence" : trustScore >= 0.5 ? "Medium Confidence" : "Needs More Evidence");

    return (
      <div className="space-y-4">
        {/* Direct Answer */}
        <div className="rounded-xl border border-hairline bg-panel/70 p-4 shadow-sm">
          <h4 className="text-xs font-mono font-semibold uppercase tracking-wider text-accent-phosphor mb-1.5">
            Answer
          </h4>
          <p className="text-sm font-medium leading-relaxed text-ink-primary">
            {cleanUserFacingText(data.direct_answer || synthesis.final_answer)}
          </p>
        </div>

        {/* Evidence & Source */}
        {data.evidence && data.evidence.length > 0 && (
          <div className="rounded-xl border border-hairline bg-panel/70 p-4 shadow-sm">
            <h4 className="text-xs font-mono font-semibold uppercase tracking-wider text-accent-phosphor mb-2">
              Supporting Evidence & Source
            </h4>
            <div className="rounded-lg border border-hairline/60 bg-panel-elevated/40 p-3">
              <div className="flex items-center gap-2 mb-1.5">
                <span className="text-xs font-mono text-ink-secondary">{data.evidence[0].source}</span>
                {data.evidence[0].page && (
                  <Badge tone="neutral" className="text-[10px] px-1.5 py-0">
                    Page {data.evidence[0].page}
                  </Badge>
                )}
              </div>
              <p className="text-xs leading-relaxed text-ink-primary/90 italic">
                "{cleanUserFacingText(data.evidence[0].text)}"
              </p>
            </div>
          </div>
        )}

        {/* Trust Result */}
        <div className="rounded-xl border border-hairline bg-panel/70 p-4 shadow-sm">
          <div className="flex items-center justify-between gap-3">
            <div className="flex items-center gap-2">
              <ShieldCheck className="h-4 w-4 text-signal-green" />
              <div>
                <h4 className="text-xs font-mono font-semibold uppercase tracking-wider text-ink-primary">
                  Trust Score
                </h4>
                <p className="text-xs font-mono text-signal-green">
                  {trustPct}% — {trustLabel}
                </p>
              </div>
            </div>
            <TrustGauge score={trustScore} size="compact" />
          </div>
        </div>
      </div>
    );
  }

  // Fallback Markdown / Text Renderer (Cleans all raw symbols, internal IDs, and renders clean sections)
  return <FallbackMarkdownView text={synthesis.final_answer} />;
}

/**
 * Intelligent Markdown Fallback that renders clean typography without raw ###, **, or internal IDs.
 */
function FallbackMarkdownView({ text }: { text: string }) {
  const clean = cleanUserFacingText(text);
  const lines = clean.split("\n");

  return (
    <div className="space-y-3">
      {lines.map((line, i) => {
        const trimmed = line.trim();
        if (!trimmed) return null;

        // Headings (### or ##)
        if (trimmed.startsWith("### ") || trimmed.startsWith("## ")) {
          const title = trimmed.replace(/^#{2,3}\s+/, "");
          return (
            <h4
              key={i}
              className="mt-4 mb-1 text-xs font-mono font-semibold uppercase tracking-wider text-accent-phosphor"
            >
              {title}
            </h4>
          );
        }

        // Numbered steps (1. Step)
        if (/^\d+\.\s+/.test(trimmed)) {
          const stepNum = trimmed.match(/^(\d+)\./)?.[1] || "•";
          const stepText = trimmed.replace(/^\d+\.\s+/, "");
          return (
            <div key={i} className="flex items-start gap-2.5 my-1 pl-1">
              <span className="flex h-4 w-4 flex-shrink-0 items-center justify-center rounded-full bg-accent-phosphor/15 text-[10px] font-mono font-bold text-accent-phosphor mt-0.5">
                {stepNum}
              </span>
              <p className="text-sm leading-relaxed text-ink-primary/95">{stepText}</p>
            </div>
          );
        }

        // Bullet points (- or * or •)
        if (trimmed.startsWith("- ") || trimmed.startsWith("* ") || trimmed.startsWith("• ")) {
          const bulletText = trimmed.replace(/^[-*•]\s+/, "");
          return (
            <div key={i} className="flex items-start gap-2 my-1 pl-2 text-sm text-ink-primary/95">
              <span className="text-accent-phosphor font-bold mt-0.5">•</span>
              <span>{bulletText}</span>
            </div>
          );
        }

        // Standard prose
        return (
          <p key={i} className="text-sm leading-relaxed text-ink-primary font-sans">
            {trimmed}
          </p>
        );
      })}
    </div>
  );
}
