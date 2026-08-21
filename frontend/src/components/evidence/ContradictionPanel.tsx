import { GitCompareArrows } from "lucide-react";
import { Card, CardBody } from "@/components/ui/Card";
import type { TrustReportResponse } from "@/types/api";

/** Shows detected contradiction pairs explicitly rather than letting them
 * blend silently into an averaged answer — the whole point of
 * contradiction-aware evidence arbitration (agents/critic/contradiction_detector.py). */
export function ContradictionPanel({ contradictions }: { contradictions: TrustReportResponse["contradictions"] }) {
  if (contradictions.length === 0) return null;

  return (
    <Card className="border-signal-red/30 bg-signal-red/5">
      <CardBody className="flex flex-col gap-3">
        <div className="flex items-center gap-2 text-signal-red">
          <GitCompareArrows className="h-4 w-4" />
          <span className="text-sm font-medium">
            {contradictions.length} contradiction{contradictions.length > 1 ? "s" : ""} detected
          </span>
        </div>
        <div className="flex flex-col gap-2">
          {contradictions.map((c, i) => (
            <div key={i} className="text-xs text-ink-primary/90 border-l-2 border-signal-red/40 pl-3">
              <span className="font-mono text-ink-muted">
                {c.chunk_id_a} ↔ {c.chunk_id_b}
              </span>
              <p className="mt-0.5">{c.explanation}</p>
            </div>
          ))}
        </div>
      </CardBody>
    </Card>
  );
}
