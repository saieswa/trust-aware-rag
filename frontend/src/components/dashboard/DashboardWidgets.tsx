import { Card, CardBody } from "@/components/ui/Card";
import type { Decision } from "@/types/api";
import { decisionColorVar, decisionLabel } from "@/lib/utils";

export function StatCard({ label, value, sublabel }: { label: string; value: string; sublabel?: string }) {
  return (
    <Card>
      <CardBody>
        <p className="text-xs uppercase tracking-wide text-ink-muted">{label}</p>
        <p className="mt-1 font-mono text-2xl font-semibold text-ink-primary">{value}</p>
        {sublabel && <p className="mt-0.5 text-xs text-ink-muted">{sublabel}</p>}
      </CardBody>
    </Card>
  );
}

/** Horizontal bar breakdown of answer / retrieve_more / abstain counts —
 * a plain, precise instrument reading rather than a decorative donut
 * chart, consistent with the rest of the design's restraint. */
export function DecisionBreakdown({ counts }: { counts: Record<Decision, number> }) {
  const total = Object.values(counts).reduce((a, b) => a + b, 0) || 1;
  const decisions: Decision[] = ["answer", "retrieve_more", "abstain"];

  return (
    <Card>
      <CardBody className="flex flex-col gap-3">
        <p className="text-xs uppercase tracking-wide text-ink-muted">Decision breakdown</p>
        {decisions.map((decision) => {
          const count = counts[decision] || 0;
          const pct = (count / total) * 100;
          return (
            <div key={decision} className="flex items-center gap-3">
              <span className="w-32 shrink-0 text-xs text-ink-primary">{decisionLabel(decision)}</span>
              <div className="h-2 flex-1 rounded-full bg-raised overflow-hidden">
                <div
                  className="h-full rounded-full transition-all duration-700"
                  style={{ width: `${pct}%`, backgroundColor: decisionColorVar(decision) }}
                />
              </div>
              <span className="w-10 shrink-0 text-right font-mono text-xs text-ink-muted">{count}</span>
            </div>
          );
        })}
      </CardBody>
    </Card>
  );
}
