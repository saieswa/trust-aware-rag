import { Badge } from "@/components/ui/Badge";
import { Card, CardBody } from "@/components/ui/Card";
import { evidenceLabelColorVar } from "@/lib/utils";
import type { ScoredEvidence } from "@/types/api";

const LABEL_TONE = { support: "green", contradict: "red", neutral: "neutral" } as const;

interface EvidenceCardProps {
  evidence: ScoredEvidence;
  highlighted?: boolean;
}

/**
 * One retrieved-and-critiqued chunk, shown as an index-card-like record:
 * source, the label the Critic Agent assigned, why, and the three
 * underlying scores (specificity, source reliability, overall quality)
 * that fed the Trust Score formula — nothing here is a black box number,
 * every score traces back to agents/critic/quality_scorer.py.
 */
export function EvidenceCard({ evidence, highlighted }: EvidenceCardProps) {
  return (
    <Card
      id={`evidence-${evidence.chunk_id}`}
      className={highlighted ? "ring-2 ring-accent-phosphor" : undefined}
    >
      <CardBody className="flex flex-col gap-3">
        <div className="flex items-start justify-between gap-3">
          <div>
            <p className="text-sm font-medium text-ink-primary">{evidence.source_title}</p>
            <p className="font-mono text-[11px] text-ink-muted mt-0.5">{evidence.chunk_id}</p>
          </div>
          <Badge tone={LABEL_TONE[evidence.label]}>{evidence.label}</Badge>
        </div>

        <p className="text-sm text-ink-primary/90 leading-relaxed">{evidence.text}</p>

        <p className="text-xs text-ink-muted italic">{evidence.reasoning}</p>

        <div className="grid grid-cols-3 gap-2 border-t border-hairline pt-3">
          <ScoreBar label="Specificity" value={evidence.specificity_score} />
          <ScoreBar label="Reliability" value={evidence.source_reliability_score} />
          <ScoreBar label="Quality" value={evidence.quality_score} color={evidenceLabelColorVar(evidence.label)} />
        </div>
      </CardBody>
    </Card>
  );
}

function ScoreBar({ label, value, color }: { label: string; value: number; color?: string }) {
  return (
    <div className="flex flex-col gap-1">
      <span className="text-[10px] uppercase tracking-wide text-ink-muted">{label}</span>
      <div className="h-1.5 rounded-full bg-raised overflow-hidden">
        <div
          className="h-full rounded-full transition-all duration-500"
          style={{ width: `${value * 100}%`, backgroundColor: color || "var(--accent-phosphor)" }}
        />
      </div>
      <span className="font-mono text-[11px] text-ink-muted">{value.toFixed(2)}</span>
    </div>
  );
}
