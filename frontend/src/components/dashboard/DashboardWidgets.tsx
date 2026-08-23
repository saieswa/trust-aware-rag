"use client";

import React, { useState } from "react";
import {
  HelpCircle,
  CheckCircle2,
  AlertTriangle,
  ShieldCheck,
  ShieldAlert,
  Info,
} from "lucide-react";
import { Card, CardBody } from "@/components/ui/Card";
import { Badge } from "@/components/ui/Badge";
import type { Decision } from "@/types/api";
import { formatPercent } from "@/lib/utils";

export interface StatCardProps {
  title: string;
  value: string | number;
  description: string;
  badge?: {
    label: string;
    tone: "green" | "amber" | "red" | "neutral";
  };
  tooltip?: string;
  icon?: React.ReactNode;
}

export function MetricSummaryCard({
  title,
  value,
  description,
  badge,
  tooltip,
  icon,
}: StatCardProps) {
  const [showTooltip, setShowTooltip] = useState(false);

  return (
    <div className="relative flex flex-col justify-between rounded-xl border border-hairline bg-panel/70 p-4 shadow-sm backdrop-blur-sm transition-all hover:border-hairline/90">
      <div>
        <div className="flex items-center justify-between gap-2 mb-1.5">
          <div className="flex items-center gap-1.5">
            {icon && <span className="text-accent-phosphor">{icon}</span>}
            <span className="text-xs font-mono font-semibold uppercase tracking-wider text-ink-muted">
              {title}
            </span>
          </div>
          {tooltip && (
            <div className="relative">
              <button
                type="button"
                onMouseEnter={() => setShowTooltip(true)}
                onMouseLeave={() => setShowTooltip(false)}
                className="text-ink-muted hover:text-ink-primary transition-colors"
                title={tooltip}
              >
                <HelpCircle className="h-3.5 w-3.5" />
              </button>
              {showTooltip && (
                <div className="absolute right-0 top-6 z-50 w-56 rounded-md border border-hairline bg-panel-elevated p-2.5 text-xs text-ink-primary shadow-xl font-sans">
                  {tooltip}
                </div>
              )}
            </div>
          )}
        </div>

        <div className="flex items-baseline gap-2 mt-1">
          <span className="font-mono text-2xl font-bold text-ink-primary">{value}</span>
          {badge && (
            <Badge tone={badge.tone} className="text-[10px] py-0 px-1.5 font-mono">
              {badge.label}
            </Badge>
          )}
        </div>
      </div>

      <p className="mt-2.5 text-xs leading-relaxed text-ink-muted">{description}</p>
    </div>
  );
}

/** Visual Trust Score Meter with Low / Moderate / High zones */
export function TrustScoreSection({ score }: { score: number }) {
  const pct = Math.round(score * 100);
  const statusLabel =
    pct >= 80 ? "High Trust" : pct >= 50 ? "Moderate Trust" : "Low Trust";
  const statusTone =
    pct >= 80 ? "text-signal-green" : pct >= 50 ? "text-accent-phosphor" : "text-signal-red";
  const badgeTone =
    pct >= 80 ? ("green" as const) : pct >= 50 ? ("amber" as const) : ("red" as const);

  return (
    <div className="rounded-xl border border-hairline bg-panel/70 p-5 shadow-sm">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 mb-4">
        <div>
          <div className="flex items-center gap-2">
            <span className="text-xs font-mono font-semibold uppercase tracking-wider text-ink-muted">
              Aggregate Trust Score
            </span>
            <Badge tone={badgeTone} className="font-mono text-[11px]">
              {statusLabel}
            </Badge>
          </div>
          <div className="flex items-baseline gap-2 mt-1">
            <span className={`font-mono text-3xl font-bold ${statusTone}`}>{pct}%</span>
            <span className="text-xs text-ink-muted font-mono">({score.toFixed(4)})</span>
          </div>
        </div>

        <p className="text-xs leading-relaxed text-ink-muted max-w-sm">
          The trust score indicates how strongly the evaluated answers are supported by retrieved evidence from your active documents.
        </p>
      </div>

      {/* Visual Tri-Zone Scale */}
      <div className="space-y-1.5">
        <div className="relative h-3 w-full rounded-full bg-raised overflow-hidden border border-hairline flex">
          <div className="h-full w-1/2 bg-signal-red/25 border-r border-hairline/30" />
          <div className="h-full w-[30%] bg-accent-phosphor/25 border-r border-hairline/30" />
          <div className="h-full w-[20%] bg-signal-green/25" />
          {/* Indicator bar */}
          <div
            className="absolute top-0 bottom-0 left-0 rounded-full transition-all duration-700 bg-gradient-to-r from-signal-red via-accent-phosphor to-signal-green opacity-90"
            style={{ width: `${Math.max(Math.min(pct, 100), 2)}%` }}
          />
        </div>

        <div className="flex justify-between text-[10px] font-mono text-ink-muted px-0.5">
          <span>0% Low Trust (0–49%)</span>
          <span>50% Moderate (50–79%)</span>
          <span className="text-right">80%–100% High Trust</span>
        </div>
      </div>
    </div>
  );
}

/** Decision Breakdown Horizontal Progress Rows */
export function DecisionBreakdownWidget({
  counts,
  total,
}: {
  counts: Record<Decision | string, number>;
  total: number;
}) {
  const safeTotal = total > 0 ? total : 1;
  const answerCount = counts.answer || 0;
  const retrieveMoreCount = counts.retrieve_more || 0;
  const abstainCount = counts.abstain || 0;

  const answerPct = Math.round((answerCount / safeTotal) * 100);
  const retrieveMorePct = Math.round((retrieveMoreCount / safeTotal) * 100);
  const abstainPct = Math.round((abstainCount / safeTotal) * 100);

  const categories = [
    {
      key: "answer",
      label: "Answer",
      count: answerCount,
      pct: answerPct,
      description: "Sufficient verified evidence was found.",
      color: "bg-signal-green",
      badgeTone: "green" as const,
      icon: <CheckCircle2 className="h-3.5 w-3.5 text-signal-green" />,
    },
    {
      key: "retrieve_more",
      label: "Needs More Evidence",
      count: retrieveMoreCount,
      pct: retrieveMorePct,
      description: "Evidence was insufficient or ambiguous.",
      color: "bg-amber-400",
      badgeTone: "amber" as const,
      icon: <AlertTriangle className="h-3.5 w-3.5 text-amber-400" />,
    },
    {
      key: "abstain",
      label: "Abstain",
      count: abstainCount,
      pct: abstainPct,
      description: "The system avoided giving an unsupported answer (safety behavior).",
      color: "bg-accent-phosphor",
      badgeTone: "neutral" as const,
      icon: <ShieldAlert className="h-3.5 w-3.5 text-accent-phosphor" />,
    },
  ];

  return (
    <div className="rounded-xl border border-hairline bg-panel/70 p-5 shadow-sm space-y-4">
      <div className="flex items-center justify-between">
        <h3 className="text-xs font-mono font-semibold uppercase tracking-wider text-ink-primary">
          Decision Breakdown
        </h3>
        <span className="text-[11px] font-mono text-ink-muted">
          {total} total evaluated
        </span>
      </div>

      <div className="space-y-3.5">
        {categories.map((cat) => (
          <div key={cat.key} className="space-y-1">
            <div className="flex items-center justify-between text-xs">
              <div className="flex items-center gap-2">
                {cat.icon}
                <span className="font-medium text-ink-primary">{cat.label}</span>
                <Badge tone={cat.badgeTone} className="font-mono text-[10px] px-1 py-0">
                  {cat.pct}%
                </Badge>
              </div>
              <span className="font-mono text-ink-secondary">
                {cat.count} question{cat.count !== 1 ? "s" : ""}
              </span>
            </div>

            <div className="h-2 w-full rounded-full bg-raised overflow-hidden border border-hairline/60">
              <div
                className={`h-full rounded-full transition-all duration-700 ${cat.color}`}
                style={{ width: `${cat.pct}%` }}
              />
            </div>
            <p className="text-[11px] text-ink-muted">{cat.description}</p>
          </div>
        ))}
      </div>
    </div>
  );
}

/** Evidence Analysis (Agreement & Contradiction) */
export function EvidenceAnalysisWidget({
  agreementScore,
  contradictionScore,
}: {
  agreementScore: number;
  contradictionScore: number;
}) {
  const agreementPct = Math.round(agreementScore * 100);
  const contradictionPct = Math.round(contradictionScore * 100);

  const agreementLabel = agreementPct >= 70 ? "High" : agreementPct >= 40 ? "Moderate" : "Low";
  const contradictionLabel =
    contradictionPct === 0 ? "Zero (Clean)" : contradictionPct <= 15 ? "Low" : "Elevated";

  return (
    <div className="rounded-xl border border-hairline bg-panel/70 p-5 shadow-sm space-y-4">
      <h3 className="text-xs font-mono font-semibold uppercase tracking-wider text-ink-primary">
        Evidence Analysis
      </h3>

      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
        {/* Agreement */}
        <div className="rounded-lg border border-hairline/70 bg-panel-elevated/40 p-3.5 space-y-2">
          <div className="flex items-center justify-between">
            <span className="text-xs font-mono text-ink-muted uppercase">Evidence Agreement</span>
            <Badge tone={agreementPct >= 70 ? "green" : "amber"} className="text-[10px] font-mono">
              {agreementLabel}
            </Badge>
          </div>
          <div className="flex items-baseline gap-2">
            <span className="font-mono text-2xl font-bold text-ink-primary">{agreementPct}%</span>
            <span className="text-xs font-mono text-ink-muted">({agreementScore.toFixed(3)})</span>
          </div>
          <p className="text-xs text-ink-muted leading-relaxed">
            Measures how often retrieved evidence was classified as supporting the evaluated answer.
          </p>
        </div>

        {/* Contradiction */}
        <div className="rounded-lg border border-hairline/70 bg-panel-elevated/40 p-3.5 space-y-2">
          <div className="flex items-center justify-between">
            <span className="text-xs font-mono text-ink-muted uppercase">Evidence Contradiction</span>
            <Badge tone={contradictionPct === 0 ? "green" : "amber"} className="text-[10px] font-mono">
              {contradictionLabel}
            </Badge>
          </div>
          <div className="flex items-baseline gap-2">
            <span className="font-mono text-2xl font-bold text-ink-primary">{contradictionPct}%</span>
            <span className="text-xs font-mono text-ink-muted">({contradictionScore.toFixed(3)})</span>
          </div>
          <p className="text-xs text-ink-muted leading-relaxed">
            Measures whether conflicting or contradictory evidence was detected among retrieved passages.
          </p>
        </div>
      </div>
    </div>
  );
}
