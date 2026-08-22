"use client";

import { useState } from "react";
import { ChevronDown, ChevronUp, FileText, CheckCircle2, XCircle, AlertCircle } from "lucide-react";
import { Badge } from "@/components/ui/Badge";
import { Card, CardBody } from "@/components/ui/Card";
import type { ScoredEvidence } from "@/types/api";

interface EvidenceCardProps {
  evidence: ScoredEvidence;
  index: number;
  highlighted?: boolean;
}

export function EvidenceCard({ evidence, index, highlighted }: EvidenceCardProps) {
  const [expanded, setExpanded] = useState(false);

  const isSupport = evidence.label === "support";
  const isContradict = evidence.label === "contradict";

  // Derive page and section if encoded in metadata / text or chunk_id
  const pageMatch = evidence.text.match(/\(Page\s+(\d+)\)/i);
  const pageNumber = pageMatch ? pageMatch[1] : null;

  // Truncate snippet for preview (first ~160 chars or first sentence)
  const fullText = evidence.text.replace(/\(Page\s+\d+\s*\|\s*[^)]+\):\s*/i, "").trim();
  const previewSnippet = fullText.length > 200 ? `${fullText.slice(0, 200)}…` : fullText;

  const relevancePct = Math.round(Math.min(evidence.final_rank_score || evidence.score, 1.0) * 100);
  const qualityPct = Math.round((evidence.quality_score || 0.5) * 100);

  return (
    <Card
      id={`evidence-${evidence.chunk_id}`}
      className={`transition-all duration-200 border ${
        highlighted
          ? "border-accent-phosphor ring-1 ring-accent-phosphor/30 shadow-md shadow-accent-phosphor/5"
          : "border-hairline hover:border-hairline-bright"
      }`}
    >
      <CardBody className="flex flex-col gap-3 p-4">
        {/* Header: Evidence Index, Document Name, Page, and Support Badge */}
        <div className="flex items-center justify-between gap-3 flex-wrap">
          <div className="flex items-center gap-2 max-w-[70%]">
            <span className="flex h-5 w-5 shrink-0 items-center justify-center rounded-full bg-raised font-mono text-[11px] font-semibold text-ink-primary border border-hairline">
              #{index + 1}
            </span>
            <FileText className="h-3.5 w-3.5 text-accent-phosphor shrink-0" />
            <span className="text-xs font-semibold text-ink-primary truncate">
              {evidence.source_title || "Document"}
            </span>
            {pageNumber && (
              <span className="rounded bg-raised px-1.5 py-0.5 font-mono text-[10px] text-ink-muted border border-hairline shrink-0">
                Page {pageNumber}
              </span>
            )}
          </div>

          <div className="flex items-center gap-2">
            {isSupport && (
              <span className="inline-flex items-center gap-1 rounded-full border border-emerald-500/20 bg-emerald-500/10 px-2.5 py-0.5 text-[11px] font-medium text-emerald-400">
                <CheckCircle2 className="h-3 w-3" />
                Supports Claim
              </span>
            )}
            {isContradict && (
              <span className="inline-flex items-center gap-1 rounded-full border border-rose-500/20 bg-rose-500/10 px-2.5 py-0.5 text-[11px] font-medium text-rose-400">
                <XCircle className="h-3 w-3" />
                Contradicts
              </span>
            )}
            {!isSupport && !isContradict && (
              <span className="inline-flex items-center gap-1 rounded-full border border-hairline bg-raised px-2.5 py-0.5 text-[11px] font-medium text-ink-muted">
                <AlertCircle className="h-3 w-3" />
                Neutral Evidence
              </span>
            )}
          </div>
        </div>

        {/* Short Relevant Excerpt */}
        <div className="rounded-md bg-raised/60 border border-hairline/60 p-3 text-xs leading-relaxed text-ink-primary">
          <p className="font-normal">{expanded ? fullText : previewSnippet}</p>
        </div>

        {/* Footer: Relevance Score, Quality Score, and Expand/Collapse Button */}
        <div className="flex items-center justify-between pt-1 border-t border-hairline/60 text-xs">
          <div className="flex items-center gap-4">
            {/* Relevance */}
            <div className="flex items-center gap-1.5">
              <span className="text-[11px] text-ink-muted">Relevance:</span>
              <span className="font-mono text-xs font-semibold text-accent-phosphor">
                {relevancePct}%
              </span>
            </div>

            {/* Quality Score */}
            <div className="flex items-center gap-1.5">
              <span className="text-[11px] text-ink-muted">Quality:</span>
              <div className="w-12 h-1.5 rounded-full bg-raised overflow-hidden border border-hairline/50">
                <div
                  className="h-full bg-emerald-400 rounded-full"
                  style={{ width: `${qualityPct}%` }}
                />
              </div>
              <span className="font-mono text-[11px] text-ink-muted">{qualityPct}%</span>
            </div>
          </div>

          {/* Show More / View Full Chunk Toggle */}
          {fullText.length > 200 && (
            <button
              onClick={() => setExpanded(!expanded)}
              className="inline-flex items-center gap-1 text-[11px] font-medium text-accent-phosphor hover:underline focus:outline-none"
            >
              <span>{expanded ? "Show Less" : "View Full Chunk"}</span>
              {expanded ? <ChevronUp className="h-3 w-3" /> : <ChevronDown className="h-3 w-3" />}
            </button>
          )}
        </div>
      </CardBody>
    </Card>
  );
}
