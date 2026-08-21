"use client";

const NODES = [
  { id: "01", label: "Retrieve" },
  { id: "02", label: "Critique" },
  { id: "03", label: "Score" },
  { id: "04", label: "Synthesize" },
  { id: "05", label: "Verify" },
];

/**
 * The hero's thesis: this product's most characteristic moment is the
 * signal traveling through five real pipeline stages before an answer is
 * shown — so the hero IS that pipeline, animated, rather than a generic
 * headline-plus-stat-block. Numbered 01-05 deliberately: this is a real
 * ordered sequence (the actual node order in agents/pipeline/agent.py),
 * not decorative numbering.
 */
export function PipelineHero() {
  return (
    <div className="w-full overflow-x-auto py-8">
      <div className="flex min-w-[640px] items-center justify-between px-4">
        {NODES.map((node, i) => (
          <div key={node.id} className="flex items-center">
            <div className="flex flex-col items-center gap-2">
              <div
                className="relative flex h-14 w-14 items-center justify-center rounded-full border-2 border-accent-phosphor/40 bg-panel font-mono text-xs text-accent-phosphor"
                style={{ animationDelay: `${i * 0.3}s` }}
              >
                <span className="absolute inset-0 rounded-full border-2 border-accent-phosphor/30 animate-ping" style={{ animationDelay: `${i * 0.4}s`, animationDuration: "2.4s" }} />
                {node.id}
              </div>
              <span className="font-mono text-[11px] text-ink-muted">{node.label}</span>
            </div>
            {i < NODES.length - 1 && (
              <div className="mx-1 h-px w-10 sm:w-16 bg-gradient-to-r from-accent-phosphor/50 to-hairline" />
            )}
          </div>
        ))}
      </div>
    </div>
  );
}
